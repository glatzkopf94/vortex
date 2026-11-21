package http

import (
	"bytes"
	"context"
	"io"
	"mime"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"time"

	"github.com/labstack/echo/v4"
)

// Only Core can reach the receiver's management socket. Media uses private RTSP.
var reolinkSocket = &net.UnixAddr{Name: "/run/vortex-reolink/control.sock", Net: "unix"}

func reolinkEndpoint(endpoint net.Addr, path string) echo.HandlerFunc {
	target := &url.URL{Scheme: "http", Host: "receiver"}
	proxy := httputil.NewSingleHostReverseProxy(target)
	proxy.Transport = &http.Transport{
		DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
			return (&net.Dialer{}).DialContext(ctx, endpoint.Network(), endpoint.String())
		},
		ResponseHeaderTimeout: 8 * time.Second,
	}
	proxy.Director = func(r *http.Request) {
		r.URL.Scheme, r.URL.Host, r.URL.Path = "http", "receiver", path
		r.URL.RawPath, r.URL.RawQuery = "", ""
		r.Header = http.Header{"Content-Type": []string{"application/json"}}
	}
	proxy.ErrorHandler = func(w http.ResponseWriter, _ *http.Request, _ error) {
		http.Error(w, "Empfangsdienst nicht erreichbar", http.StatusServiceUnavailable)
	}
	return func(c echo.Context) error {
		r := c.Request()
		if r.Method == http.MethodPost {
			mediaType, _, _ := mime.ParseMediaType(r.Header.Get("Content-Type"))
			if mediaType != "application/json" {
				return c.NoContent(http.StatusUnsupportedMediaType)
			}
			data, err := io.ReadAll(io.LimitReader(r.Body, 8193))
			if err != nil || len(data) == 0 {
				return c.NoContent(http.StatusBadRequest)
			}
			if len(data) > 8192 {
				return c.NoContent(http.StatusRequestEntityTooLarge)
			}
			r.Body = io.NopCloser(bytes.NewReader(data))
			r.ContentLength = int64(len(data))
			r.TransferEncoding = nil
		}
		proxy.ServeHTTP(c.Response(), r)
		return nil
	}
}
