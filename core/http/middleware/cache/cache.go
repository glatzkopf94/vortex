// Modified 2026-10-10: bounded response capture and exact-sized retained bodies.
// Package cache is an in-memory LRU cache middleware
package cache

import (
	"bytes"
	"fmt"
	"net/http"
	"path"
	"strings"

	"github.com/datarhei/core/v16/http/cache"

	"github.com/labstack/echo/v4"
	"github.com/labstack/echo/v4/middleware"
)

type Config struct {
	Skipper middleware.Skipper
	Cache   cache.Cacher
	Headers []string
	Prefix  string
}

var DefaultConfig = Config{
	Skipper: middleware.DefaultSkipper,
	Cache:   nil,
	Headers: []string{"Content-Type"},
	Prefix:  "",
}

func New() echo.MiddlewareFunc {
	return NewWithConfig(DefaultConfig)
}

func NewWithConfig(config Config) echo.MiddlewareFunc {
	// Defaults
	if config.Skipper == nil {
		config.Skipper = DefaultConfig.Skipper
	}

	if config.Headers == nil {
		config.Headers = DefaultConfig.Headers
	}

	return func(next echo.HandlerFunc) echo.HandlerFunc {
		return func(c echo.Context) error {
			if config.Skipper(c) {
				return next(c)
			}

			if config.Cache == nil {
				return next(c)
			}

			req := c.Request()
			res := c.Response()

			if req.Header.Get("Range") != "" {
				res.Header().Set("X-Cache", "SKIP RANGE")
				return next(c)
			}

			if req.Method != "GET" {
				res.Header().Set("X-Cache", "SKIP ONLYGET")
				return next(c)
			}

			key := strings.TrimPrefix(req.URL.Path, config.Prefix)

			if !config.Cache.IsExtensionCacheable(path.Ext(req.URL.Path)) {
				res.Header().Set("X-Cache", "SKIP EXT")
				return next(c)
			}

			if obj, expireIn, _ := config.Cache.Get(key); obj == nil {
				// cache miss
				writer := res.Writer

				w := &cacheWriter{
					header:    writer.Header().Clone(),
					writer:    writer,
					cacheable: config.Cache.IsSizeCacheable,
				}
				res.Writer = w

				if err := next(c); err != nil {
					c.Error(err)
				}

				// Restore original writer
				res.Writer = writer

				if w.streamed {
					return w.err
				}

				// Preserve response headers, including content range and length.
				for k, v := range w.header {
					res.Header()[k] = append([]string(nil), v...)
				}

				if w.code == 0 {
					w.code = http.StatusOK
				}
				res.Status = w.code

				defer writer.Write(w.body.Bytes())

				if res.Status != 200 {
					res.Header().Set("X-Cache", "SKIP NOTOK")
					res.Writer.WriteHeader(res.Status)
					return nil
				}

				size := uint64(w.body.Len())

				if !config.Cache.IsSizeCacheable(size) {
					res.Header().Set("X-Cache", "SKIP TOOBIG")
					res.Writer.WriteHeader(res.Status)
					return nil
				}

				retained := make([]byte, w.body.Len())
				copy(retained, w.body.Bytes())
				o := &cacheObject{
					status: res.Status,
					body:   retained,
					header: w.header.Clone(),
				}

				if err := config.Cache.Put(key, o, size); err != nil {
					res.Header().Set("X-Cache", "SKIP TOOBIG")
					res.Writer.WriteHeader(res.Status)
					return nil
				}

				res.Header().Set("Cache-Control", fmt.Sprintf("max-age=%.0f", expireIn.Seconds()))
				res.Header().Set("X-Cache", "MISS")
				res.Writer.WriteHeader(res.Status)
			} else {
				// cache hit
				o := obj.(*cacheObject)

				// overwrite the header with the cached headers
				copyCacheHeaders(res.Header(), o.header, config.Headers)

				res.Header().Set("Cache-Control", fmt.Sprintf("max-age=%.0f", expireIn.Seconds()))
				res.Header().Set("X-Cache", fmt.Sprintf("HIT %.3f", expireIn.Seconds()))

				res.WriteHeader(o.status)
				res.Write(o.body)
			}

			return nil
		}
	}
}

func copyCacheHeaders(dst, src http.Header, headers []string) {
	if len(headers) == 0 {
		return
	}

	for _, key := range headers {
		values := src.Values(key)
		if len(values) == 0 {
			continue
		}

		dst.Set(key, values[0])
		for _, v := range values[1:] {
			dst.Add(key, v)
		}
	}
}

type cacheObject struct {
	status int
	body   []byte
	header http.Header
}

type cacheWriter struct {
	code      int
	header    http.Header
	body      bytes.Buffer
	writer    http.ResponseWriter
	cacheable func(uint64) bool
	streamed  bool
	err       error
}

func (w *cacheWriter) Header() http.Header {
	if w.header == nil {
		w.header = make(http.Header)
	}

	return w.header
}

func (w *cacheWriter) WriteHeader(code int) {
	if w.code == 0 {
		w.code = code
	}
}

func (w *cacheWriter) Write(body []byte) (int, error) {
	if w.code == 0 {
		w.WriteHeader(http.StatusOK)
	}
	if !w.streamed && (uint64(w.body.Len())+uint64(len(body)) > 8*1024*1024 || (w.cacheable != nil && !w.cacheable(uint64(w.body.Len())+uint64(len(body))))) {
		w.stream("SKIP TOOBIG")
	}
	if w.err != nil {
		return 0, w.err
	}
	if w.streamed {
		n, err := w.writer.Write(body)
		if err != nil {
			w.err = err
		}
		return n, err
	}
	return w.body.Write(body)
}

// Switch to pass-through before capturing an oversized chunk. Never truncate delivery.
func (w *cacheWriter) stream(reason string) {
	if w.streamed {
		return
	}
	w.streamed = true
	if w.code == 0 {
		w.code = http.StatusOK
	}
	for k, v := range w.header {
		w.writer.Header()[k] = append([]string(nil), v...)
	}
	w.writer.Header().Set("X-Cache", reason)
	w.writer.WriteHeader(w.code)
	if w.body.Len() > 0 {
		_, w.err = w.writer.Write(w.body.Bytes())
	}
	w.body = bytes.Buffer{}
}

func (w *cacheWriter) Flush() {
	w.stream("SKIP FLUSH")
	if f, ok := w.writer.(http.Flusher); ok {
		f.Flush()
	}
}
