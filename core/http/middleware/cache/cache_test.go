package cache

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/datarhei/core/v16/http/cache"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/require"
)

func TestCache(t *testing.T) {
	c, err := cache.NewLRUCache(cache.LRUConfig{
		TTL:             300 * time.Second,
		MaxSize:         0,
		MaxFileSize:     16,
		AllowExtensions: []string{".js"},
		BlockExtensions: []string{".ts"},
		Logger:          nil,
	})

	require.NoError(t, err)

	e := echo.New()
	req := httptest.NewRequest(http.MethodGet, "/found.js", nil)
	rec := httptest.NewRecorder()
	ctx := e.NewContext(req, rec)

	handler := NewWithConfig(Config{
		Cache: c,
	})(func(c echo.Context) error {
		if c.Request().URL.Path == "/found.js" {
			c.Response().Write([]byte("test"))
		} else if c.Request().URL.Path == "/toobig.js" {
			c.Response().Write([]byte("testtesttesttesttest"))
		} else if c.Request().URL.Path == "/blocked.ts" {
			c.Response().Write([]byte("blocked"))
		}

		c.Response().WriteHeader(http.StatusNotFound)
		return nil
	})

	handler(ctx)

	require.Equal(t, "test", rec.Body.String())
	require.Equal(t, 200, rec.Result().StatusCode)
	require.Equal(t, "MISS", rec.Result().Header.Get("x-cache"))

	rec = httptest.NewRecorder()
	ctx = e.NewContext(req, rec)

	handler(ctx)

	require.Equal(t, "test", rec.Body.String())
	require.Equal(t, 200, rec.Result().StatusCode)
	require.Equal(t, "HIT", rec.Result().Header.Get("x-cache")[:3])

	req = httptest.NewRequest(http.MethodGet, "/notfound.js", nil)
	rec = httptest.NewRecorder()
	ctx = e.NewContext(req, rec)

	handler(ctx)

	require.Equal(t, 404, rec.Result().StatusCode)
	require.Equal(t, "SKIP NOTOK", rec.Result().Header.Get("x-cache"))

	req = httptest.NewRequest(http.MethodGet, "/toobig.js", nil)
	rec = httptest.NewRecorder()
	ctx = e.NewContext(req, rec)

	handler(ctx)

	require.Equal(t, "testtesttesttesttest", rec.Body.String())
	require.Equal(t, 200, rec.Result().StatusCode)
	require.Equal(t, "SKIP TOOBIG", rec.Result().Header.Get("x-cache"))

	req = httptest.NewRequest(http.MethodGet, "/blocked.ts", nil)
	rec = httptest.NewRecorder()
	ctx = e.NewContext(req, rec)

	handler(ctx)

	require.Equal(t, "blocked", rec.Body.String())
	require.Equal(t, 200, rec.Result().StatusCode)
	require.Equal(t, "SKIP EXT", rec.Result().Header.Get("x-cache"))

	req = httptest.NewRequest(http.MethodPost, "/found.js", nil)
	rec = httptest.NewRecorder()
	ctx = e.NewContext(req, rec)

	handler(ctx)

	require.Equal(t, "test", rec.Body.String())
	require.Equal(t, 200, rec.Result().StatusCode)
	require.Equal(t, "SKIP ONLYGET", rec.Result().Header.Get("x-cache"))
}

// Regression: oversized chunked responses must stream without retaining a copy.
func TestOversizedCaptureStreamsAndPreservesHeaders(t *testing.T) {
	rec := httptest.NewRecorder()
	w := &cacheWriter{writer: rec, header: make(http.Header), cacheable: func(n uint64) bool { return n <= 16 }}
	w.Header().Set("Content-Type", "video/mp4")
	w.Header().Set("Content-Length", "24")
	for i := 0; i < 3; i++ {
		n, err := w.Write([]byte("12345678"))
		require.NoError(t, err)
		require.Equal(t, 8, n)
	}
	require.True(t, w.streamed)
	require.Zero(t, w.body.Cap())
	require.Equal(t, "123456781234567812345678", rec.Body.String())
	require.Equal(t, "24", rec.Result().Header.Get("Content-Length"))
}

func TestRangeBypassesCachedFullResponse(t *testing.T) {
	cacheStore, err := cache.NewLRUCache(cache.LRUConfig{TTL: time.Minute, MaxFileSize: 128})
	require.NoError(t, err)
	defer cacheStore.Purge()
	e := echo.New()
	h := NewWithConfig(Config{Cache: cacheStore})(func(c echo.Context) error {
		if c.Request().Header.Get("Range") != "" {
			c.Response().Header().Set("Content-Range", "bytes 1-2/4")
			return c.String(206, "es")
		}
		return c.String(200, "test")
	})
	full := httptest.NewRecorder()
	require.NoError(t, h(e.NewContext(httptest.NewRequest("GET", "/v.mp4", nil), full)))
	req := httptest.NewRequest("GET", "/v.mp4", nil)
	req.Header.Set("Range", "bytes=1-2")
	rec := httptest.NewRecorder()
	require.NoError(t, h(e.NewContext(req, rec)))
	require.Equal(t, 206, rec.Code)
	require.Equal(t, "es", rec.Body.String())
	require.Equal(t, "bytes 1-2/4", rec.Header().Get("Content-Range"))
}

func TestFlushDoesNotCachePartialResponse(t *testing.T) {
	rec := httptest.NewRecorder()
	w := &cacheWriter{writer: rec, header: make(http.Header), cacheable: func(uint64) bool { return true }}
	_, err := w.Write([]byte("first"))
	require.NoError(t, err)
	w.Flush()
	_, err = w.Write([]byte("second"))
	require.NoError(t, err)
	require.True(t, w.streamed)
	require.Zero(t, w.body.Cap())
	require.Equal(t, "firstsecond", rec.Body.String())
}

func TestCacheCountsDeliveredBytesOnce(t *testing.T) {
	store, err := cache.NewLRUCache(cache.LRUConfig{TTL: time.Minute, MaxFileSize: 128})
	require.NoError(t, err)
	defer store.Purge()
	h := NewWithConfig(Config{Cache: store})(func(c echo.Context) error { return c.String(200, "12345678901234567") })
	e := echo.New()
	for i := 0; i < 2; i++ {
		ctx := e.NewContext(httptest.NewRequest("GET", "/file", nil), httptest.NewRecorder())
		require.NoError(t, h(ctx))
		require.Equal(t, int64(17), ctx.Response().Size)
	}
	obj, _, err := store.Get("/file")
	require.NoError(t, err)
	body := obj.(*cacheObject).body
	require.Equal(t, len(body), cap(body))
}
