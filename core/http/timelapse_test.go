package http

import (
	"github.com/labstack/echo/v4"
	"github.com/stretchr/testify/require"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestTimelapseProxySeparatesPublicAndAdmin(t *testing.T) {
	listener, err := net.Listen("tcp", "127.0.0.1:8099")
	require.NoError(t, err)
	backend := &http.Server{Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		require.Empty(t, r.Header.Get("Authorization"))
		require.Empty(t, r.Header.Get("Cookie"))
		io.WriteString(w, r.URL.Path)
	})}
	go backend.Serve(listener)
	defer backend.Close()
	e := echo.New()
	for _, test := range []struct {
		path, expected string
		public         bool
	}{
		{"/timelapse/channel/test", "/public/channel/test", true},
		{"/timelapse/admin/status", "/public/admin/status", true},
		{"/api/v3/timelapse/status", "/admin/status", false},
	} {
		req := httptest.NewRequest(http.MethodGet, test.path, strings.NewReader(""))
		req.Header.Set("Authorization", "Bearer private")
		req.Header.Set("Cookie", "secret=value")
		rec := httptest.NewRecorder()
		require.NoError(t, timelapseProxy(test.public)(e.NewContext(req, rec)))
		require.Equal(t, test.expected, rec.Body.String())
	}
}
