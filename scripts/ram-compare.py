#!/usr/bin/env python3
"""Read-only RAM snapshot. No credentials, stream URLs, restarts or cache purges."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess


def command(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=20)
    if p.returncode:raise RuntimeError(p.stderr.strip()[:200])
    return p.stdout


def fields(path):
    result={}
    for line in Path(path).read_text().splitlines():
        parts=line.replace(':',' ').split()
        if len(parts)>1 and parts[1].isdigit():result[parts[0]]=int(parts[1])
    return result


def snapshot(names):
    result={'at':datetime.now(timezone.utc).isoformat(),'host_kib':{},'containers':[]}
    host=fields('/proc/meminfo')
    result['host_kib']={k:host.get(k) for k in ['MemTotal','MemAvailable','Cached','SReclaimable','AnonPages','SwapTotal','SwapFree']}
    for name in names:
        item={'name':name};result['containers'].append(item)
        try:
            info=json.loads(command(['docker','inspect',name]))[0]
            item.update(image=info['Config']['Image'],started=info['State']['StartedAt'],restarts=info.get('RestartCount'),running=info['State']['Running'])
            if not item['running']:continue
            pid=info['State']['Pid']
            for line in Path(f'/proc/{pid}/cgroup').read_text().splitlines():
                if line.startswith('0::'):
                    folder=Path('/sys/fs/cgroup')/line[3:].lstrip('/')
                    try:
                        cg=fields(folder/'memory.stat')
                        item['cgroup_bytes']={k:cg.get(k) for k in ['anon','file','kernel','slab','inactive_file','active_file','shmem']}
                        for k in ['memory.current','memory.swap.current']:item['cgroup_bytes'][k]=int((folder/k).read_text())
                    except OSError:item['cgroup_note']='Host cgroup path not readable; use process data.'
            sums=defaultdict(lambda:defaultdict(int));count=defaultdict(int)
            for line in command(['docker','top',name,'-eo','pid,comm']).splitlines()[1:]:
                parts=line.split(None,1)
                if len(parts)!=2 or not parts[0].isdigit():continue
                process_id,kind=parts;kind=kind.strip();count[kind]+=1
                try:
                    status=fields(f'/proc/{process_id}/status')
                    for k in ['VmRSS','RssAnon','RssFile','VmSwap']:sums[kind][k]+=status.get(k,0)
                    try:
                        roll=fields(f'/proc/{process_id}/smaps_rollup')
                        for k in ['Pss','Private_Dirty','Private_Clean','SwapPss']:sums[kind][k]+=roll.get(k,0)
                    except OSError:pass
                except OSError:pass
            item['process_groups_kib']=[{'name':k,'count':count[k],**v} for k,v in sorted(sums.items(),key=lambda x:-x[1]['VmRSS'])]
            env={v.split('=',1)[0]:v.split('=',1)[1] for v in info['Config'].get('Env',[]) if '=' in v}
            item['cache_environment']={k:v for k,v in env.items() if k.startswith('CORE_STORAGE_DISK_CACHE_') or k in ['CORE_STORAGE_MEMORY_MAX_SIZE_MBYTES','CORE_STORAGE_MEMORY_PURGE','CORE_DEBUG_MEMORY_LIMIT_MBYTES']}
            config=env.get('CORE_CONFIGFILE','/core/config/config.json')
            for mount in info['Mounts']:
                dest=mount['Destination'].rstrip('/')
                if config.startswith(dest+'/'):
                    try:
                        cfg=json.loads((Path(mount['Source'])/config[len(dest)+1:]).read_text())
                        storage=cfg.get('storage',{})
                        item['saved_disk_cache']=storage.get('disk',{}).get('cache',{})
                        item['saved_memory_storage']={k:storage.get('memory',{}).get(k) for k in ['max_size_mbytes','purge']}
                    except (OSError,ValueError):pass
                    break
        except (OSError,RuntimeError,ValueError,subprocess.TimeoutExpired) as e:item['error']=str(e)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('containers',nargs='*',default=['restreamer-main-nkl','restreamer-timelapse-test'])
    parser.add_argument('--append',help='Append one JSON snapshot to this file for later comparison')
    args=parser.parse_args();data=snapshot(args.containers)
    print(json.dumps(data,ensure_ascii=False,indent=2))
    if args.append:
        with Path(args.append).open('a') as output:output.write(json.dumps(data,ensure_ascii=False)+'\n')
