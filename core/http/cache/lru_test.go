package cache

import (
	"fmt"
	"testing"
	"time"

	"github.com/stretchr/testify/require"
)

var defaultConfig = LRUConfig{
	TTL:             time.Hour,
	MaxSize:         128,
	MaxFileSize:     0,
	AllowExtensions: []string{".html", ".js", ".jpg"},
	BlockExtensions: []string{".m3u8"},
	Logger:          nil,
}

func getCache(t *testing.T) *lrucache {
	cache, err := NewLRUCache(defaultConfig)
	require.Equal(t, nil, err)

	return cache.(*lrucache)
}

func TestNew(t *testing.T) {
	_, err := NewLRUCache(LRUConfig{
		TTL:         time.Hour,
		MaxSize:     128,
		MaxFileSize: 129,
	})
	require.NotEqual(t, nil, err)

	_, err = NewLRUCache(LRUConfig{
		TTL:         time.Hour,
		MaxSize:     0,
		MaxFileSize: 129,
	})
	require.Equal(t, nil, err)

	_, err = NewLRUCache(LRUConfig{
		TTL:         time.Hour,
		MaxSize:     128,
		MaxFileSize: 127,
	})
	require.Equal(t, nil, err)
}

func TestPut(t *testing.T) {
	cache := getCache(t)

	data, _, err := cache.Get("foobar")
	require.Equal(t, nil, data)
	require.Equal(t, nil, err)

	err = cache.Put("foobar", "hello", 64)
	require.Equal(t, nil, err)

	data, _, err = cache.Get("foobar")
	require.Equal(t, "hello", data)
	require.Equal(t, nil, err)
}

func TestPutTooBig(t *testing.T) {
	cache := getCache(t)

	err := cache.Put("foobar", "hello", 129)
	require.NotEqual(t, nil, err)
}

func TestPurge(t *testing.T) {
	cache := getCache(t)

	data, _, err := cache.Get("foobar")
	require.Equal(t, nil, data)
	require.Equal(t, nil, err)

	err = cache.Put("foobar", "hello", 64)
	require.Equal(t, nil, err)

	data, _, err = cache.Get("foobar")
	require.NotEqual(t, nil, data)
	require.Equal(t, nil, err)

	err = cache.Delete("foobar")
	require.Equal(t, nil, err)

	data, _, err = cache.Get("foobar")
	require.Equal(t, nil, data)
	require.Equal(t, nil, err)
}

func TestLRU(t *testing.T) {
	cache := getCache(t)

	err := cache.Put("1", "hello", 32)
	require.Equal(t, nil, err)

	err = cache.Put("2", "hello", 32)
	require.Equal(t, nil, err)

	err = cache.Put("3", "hello", 32)
	require.Equal(t, nil, err)

	err = cache.Put("4", "hello", 32)
	require.Equal(t, nil, err)

	data, _, _ := cache.Get("1")
	require.NotEqual(t, nil, data)

	data, _, _ = cache.Get("2")
	require.NotEqual(t, nil, data)

	data, _, _ = cache.Get("3")
	require.NotEqual(t, nil, data)

	data, _, _ = cache.Get("4")
	require.NotEqual(t, nil, data)

	data, _, _ = cache.Get("5")
	require.Equal(t, nil, data)

	err = cache.Put("5", "hello", 32)
	require.Equal(t, nil, err)

	data, _, _ = cache.Get("1")
	require.Equal(t, nil, data)

	data, _, _ = cache.Get("2")
	require.NotEqual(t, nil, data)

	data, _, _ = cache.Get("3")
	require.NotEqual(t, nil, data)

	data, _, _ = cache.Get("4")
	require.NotEqual(t, nil, data)

	data, _, _ = cache.Get("5")
	require.NotEqual(t, nil, data)
}

func TestAllowExtension(t *testing.T) {
	cache := getCache(t)

	r := cache.IsExtensionCacheable(".html")
	require.Equal(t, true, r)

	r = cache.IsExtensionCacheable(".png")
	require.Equal(t, false, r)
}

func TestBlockExtension(t *testing.T) {
	cache := getCache(t)
	cache.allowExtensions = []string{}

	r := cache.IsExtensionCacheable(".html")
	require.Equal(t, true, r)

	r = cache.IsExtensionCacheable(".m3u8")
	require.Equal(t, false, r)
}

func TestSize(t *testing.T) {
	cache := getCache(t)

	r := cache.IsSizeCacheable(127)
	require.Equal(t, true, r)

	r = cache.IsSizeCacheable(128)
	require.Equal(t, true, r)

	r = cache.IsSizeCacheable(129)
	require.Equal(t, false, r)
}

// A DVR segment is never requested again after playback. TTL must release it
// without a Get, and the expiry worker must stop once the cache is empty.
func TestExpiresUnreadDVRSegments(t *testing.T) {
	raw, err := NewLRUCache(LRUConfig{TTL: 20 * time.Millisecond})
	require.NoError(t, err)
	c := raw.(*lrucache)
	defer c.Purge()
	for i := 0; i < 200; i++ {
		require.NoError(t, c.Put(fmt.Sprintf("segment-%d.ts", i), make([]byte, 16384), 16384))
	}
	require.Eventually(t, func() bool {
		c.lock.Lock()
		defer c.lock.Unlock()
		return len(c.objects) == 0 && c.list.Len() == 0 && c.size == 0 && c.expiryTimer == nil
	}, time.Second, time.Millisecond)
}

func TestExpiryAndPurgeReuse(t *testing.T) {
	raw, _ := NewLRUCache(LRUConfig{TTL: 20 * time.Millisecond})
	c := raw.(*lrucache)
	defer c.Purge()
	require.NoError(t, c.Put("replaced", "before", 6))
	require.NoError(t, c.Put("replaced", "after", 5))
	got, _, err := c.Get("replaced")
	require.NoError(t, err)
	require.Equal(t, "after", got)
	c.Purge()
	require.NoError(t, c.Put("new", "new", 3))
	got, _, err = c.Get("new")
	require.NoError(t, err)
	require.Equal(t, "new", got)
	require.Eventually(t, func() bool {
		c.lock.Lock()
		defer c.lock.Unlock()
		return c.size == 0 && c.expiryTimer == nil && len(c.objects) == 0
	}, time.Second, time.Millisecond)
}
