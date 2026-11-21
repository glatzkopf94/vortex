package http

import (
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/require"
)

func TestReolinkProxy(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	require.NoError(t, err)
	backend := http.Server{Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/save" || r.Header.Get("Authorization") != "" || r.Header.Get("Cookie") != "" || r.ContentLength != 2 {
			w.WriteHeader(400)
			return
		}
		io.Copy(w, r.Body)
	})}
	go backend.Serve(ln)
	defer backend.Close()
	for _, tc := range []struct {
		content, media string
		code           int
	}{
		{"{}", "application/json", 200}, {"{}", "text/plain", 415}, {strings.Repeat("x", 8193), "application/json", 413},
	} {
		req := httptest.NewRequest("POST", "/api/v3/reolink/save", strings.NewReader(tc.content))
		req.ContentLength = -1
		req.Header.Set("Content-Type", tc.media)
		req.Header.Set("Authorization", "Bearer test")
		req.Header.Set("Cookie", "session=test")
		rec := httptest.NewRecorder()
		require.NoError(t, reolinkEndpoint(ln.Addr(), "/save")(echo.New().NewContext(req, rec)))
		require.Equal(t, tc.code, rec.Code)
	}
}
