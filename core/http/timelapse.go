package http

import (
	"net/http"
	"net/http/httputil"
	"net/url"
	"strings"
	"time"

	"github.com/labstack/echo/v4"
)

// The worker is loopback-only. Administrative routes inherit Core JWT/access
// middleware; the public routes are read-only and publication-filtered by it.
func timelapseProxy(public bool) echo.HandlerFunc {
	target, _ := url.Parse("http://127.0.0.1:8099")
	proxy := httputil.NewSingleHostReverseProxy(target)
	proxy.Transport = &http.Transport{ResponseHeaderTimeout: 10 * time.Second, IdleConnTimeout: 30 * time.Second}
	director := proxy.Director
	proxy.Director = func(r *http.Request) {
		director(r)
		if public {
			r.URL.Path = "/public" + strings.TrimPrefix(r.URL.Path, "/timelapse")
		} else {
			r.URL.Path = "/admin" + strings.TrimPrefix(r.URL.Path, "/api/v3/timelapse")
		}
		r.Header.Del("Authorization")
		r.Header.Del("Cookie")
	}
	proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
		http.Error(w, "Zeitrafferdienst nicht erreichbar", http.StatusServiceUnavailable)
	}
	return func(c echo.Context) error {
		proxy.ServeHTTP(c.Response(), c.Request())
		return nil
	}
}
