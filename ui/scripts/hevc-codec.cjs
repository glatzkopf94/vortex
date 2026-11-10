// ISO/IEC 14496-15: derive RFC 6381 HEVC codec parameters from hvcC.
// Self-contained: embedded into mux.js and Video.js' worker bundle at build time.
function hevcCodecFromSampleEntry(codec, entry) {
  if (!/^(hvc1|hev1)$/i.test(codec) || !entry || entry.length < 86) return codec;
  const u32 = (p) => (entry[p] * 16777216 + entry[p+1] * 65536 + entry[p+2] * 256 + entry[p+3]);
  let offset = 78; // VisualSampleEntry payload, without its box header.
  while (offset + 8 <= entry.length) {
    let size = u32(offset), header = 8;
    if (size === 1) {
      if (offset + 16 > entry.length || u32(offset+8) !== 0) return codec;
      size = u32(offset+12); header = 16;
    } else if (size === 0) size = entry.length - offset;
    if (size < header || size > entry.length-offset) return codec;
    const type = String.fromCharCode.apply(null, entry.subarray(offset+4, offset+8));
    if (type === 'hvcC') {
      const b = entry.subarray(offset+header, offset+size);
      if (b.length < 23 || b[0] !== 1) return codec;
      // Reject truncated parameter-set arrays rather than inventing a codec.
      let p=23;
      for(let i=0;i<b[22];i++) {
        if(p+3>b.length)return codec;
        const count=b[p+1]*256+b[p+2];p+=3;
        for(let n=0;n<count;n++) {
          if(p+2>b.length)return codec;
          const len=b[p]*256+b[p+1];p+=2;
          if(!len||p+len>b.length)return codec;
          p+=len;
        }
      }
      const space=['','A','B','C'][b[1]>>>6];
      let compatibility=0;
      // general_profile_compatibility_flags, bit-reversed per codec-string syntax.
      for(let bit=0;bit<32;bit++)
        compatibility=(compatibility*2+((b[2+((31-bit)>>>3)]>>>(bit%8))&1))>>>0;
      let value=codec.toLowerCase()+'.'+space+(b[1]&31)+'.'+compatibility.toString(16).toUpperCase()+'.'+((b[1]&32)?'H':'L')+b[12];
      let last=11;while(last>=6&&b[last]===0)last--;
      // Strip only trailing zero constraint bytes; preserve internal zero bytes.
      for(let i=6;i<=last;i++)value+='.'+b[i].toString(16).toUpperCase().padStart(2,'0');
      return value;
    }
    offset+=size;
  }
  return codec;
}
module.exports={hevcCodecFromSampleEntry};
