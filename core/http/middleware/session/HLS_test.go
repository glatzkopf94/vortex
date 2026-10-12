package session

import (
	"container/list"
	"fmt"
	"net/url"
	"strings"
	"testing"
	"time"
)

func TestRewriteHLSPreservesViewerID(t *testing.T) {
	rewriter := sessionRewriter{}
	rewriter.buffer.WriteString("#EXTM3U\nsegment.ts\n")
	requestURL, err := url.Parse("https://stream.example.test/channel.m3u8?viewer=viewer-browser-0001")
	if err != nil {
		t.Fatal(err)
	}

	rewriter.rewriteHLS("session-id", requestURL)
	result := rewriter.buffer.String()
	if !strings.Contains(result, "viewer=viewer-browser-0001") {
		t.Fatalf("viewer ID missing from rewritten playlist: %s", result)
	}
}

func TestRewriteHLSDropsInvalidViewerID(t *testing.T) {
	rewriter := sessionRewriter{}
	rewriter.buffer.WriteString("#EXTM3U\nsegment.ts\n")
	requestURL, err := url.Parse("https://stream.example.test/channel.m3u8?viewer=../../invalid")
	if err != nil {
		t.Fatal(err)
	}

	rewriter.rewriteHLS("session-id", requestURL)
	result := rewriter.buffer.String()
	if strings.Contains(result, "viewer=") {
		t.Fatalf("invalid viewer ID propagated to playlist: %s", result)
	}
}

func TestPendingSegmentsBoundedAndExpired(t *testing.T) {
	h := hls{rxsegments: make(map[string]*list.Element)}
	now := time.Now()
	for i := 0; i < pendingSegmentLimit+100; i++ {
		h.rememberSegment(fmt.Sprintf("/stream/%d.ts", i), 123, now)
	}
	if len(h.rxsegments) != pendingSegmentLimit || h.rxorder.Len() != pendingSegmentLimit {
		t.Fatal("pending accounting exceeds limit")
	}
	if _, ok := h.rxsegments["/stream/0.ts"]; ok {
		t.Fatal("oldest record was not evicted")
	}
	h.rememberSegment("/new.ts", 456, now.Add(pendingSegmentTTL))
	if len(h.rxsegments) != 1 || h.rxorder.Len() != 1 {
		t.Fatal("expired records retained")
	}
	h.rememberSegment("/new.ts", 789, now.Add(pendingSegmentTTL+time.Second))
	if h.rxorder.Len() != 1 || h.rxsegments["/new.ts"].Value.(pendingSegment).size != 789 {
		t.Fatal("duplicate accounting record")
	}
}
