package update

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"regexp"
	"strings"
	"sync"
	"time"

	"github.com/datarhei/core/v16/log"
	"github.com/datarhei/core/v16/monitor/metric"
	"golang.org/x/mod/semver"
)

const defaultReleaseAPI = "https://api.github.com/repos/glatzkopf94/vortex/releases/latest"

var developmentVersion = regexp.MustCompile(`^(v\d+\.\d+\.\d+)-dev(\d+)$`)

// Config is the configuration for the update check. The identity, architecture,
// and monitor fields remain for source compatibility with the upstream Core,
// but the NKL checker never transmits them.
type Config struct {
	ID         string
	Name       string
	Version    string
	Arch       string
	Monitor    metric.Reader
	ReleaseAPI string
	Logger     log.Logger
}

// Checker periodically checks the public NKL GitHub release metadata.
type Checker interface {
	Start()
	Stop()
}

type checker struct {
	version    string
	releaseAPI string

	startOnce  sync.Once
	stopOnce   sync.Once
	stopTicker context.CancelFunc

	logger log.Logger
}

// New creates an NKL update checker. No installation identifier, metrics,
// viewer counts, or other usage data are sent.
func New(config Config) (Checker, error) {
	version := normalizeVersion(config.Version)
	if !semver.IsValid(version) {
		return nil, fmt.Errorf("invalid current version: %s", config.Version)
	}

	releaseAPI := strings.TrimSpace(config.ReleaseAPI)
	if releaseAPI == "" {
		releaseAPI = defaultReleaseAPI
	}

	s := &checker{
		version:    version,
		releaseAPI: releaseAPI,
		logger:     config.Logger,
	}
	if s.logger == nil {
		s.logger = log.New("")
	}

	// Drain stop once so Stop can't be called before Start has initialized the
	// cancellation function.
	s.stopOnce.Do(func() {})

	return s, nil
}

func normalizeVersion(value string) string {
	version := strings.TrimSpace(value)
	if !strings.HasPrefix(version, "v") {
		version = "v" + version
	}
	return developmentVersion.ReplaceAllString(version, `${1}-dev.${2}`)
}

func (s *checker) tick(ctx context.Context, interval, delay time.Duration) {
	timer := time.NewTimer(delay)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return
	case <-timer.C:
	}

	if err := s.check(); err != nil {
		s.logger.WithError(err).Warn().Log("Failed to check NKL releases")
	}

	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			if err := s.check(); err != nil {
				s.logger.WithError(err).Warn().Log("Failed to check NKL releases")
			}
		}
	}
}

func (s *checker) Start() {
	s.startOnce.Do(func() {
		ctx, cancel := context.WithCancel(context.Background())
		s.stopTicker = cancel
		go s.tick(ctx, 24*time.Hour, 10*time.Second)
		s.stopOnce = sync.Once{}
	})
}

func (s *checker) Stop() {
	s.stopOnce.Do(func() {
		if s.stopTicker != nil {
			s.stopTicker()
		}
		s.startOnce = sync.Once{}
	})
}

type releaseResponse struct {
	TagName string `json:"tag_name"`
	HTMLURL string `json:"html_url"`
}

func (s *checker) check() error {
	client := &http.Client{Timeout: 10 * time.Second}
	req, err := http.NewRequest(http.MethodGet, s.releaseAPI, nil)
	if err != nil {
		return err
	}
	req.Header.Set("Accept", "application/vnd.github+json")
	req.Header.Set("User-Agent", "NKL-Restreamer-Update-Checker")

	res, err := client.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()
	if res.StatusCode != http.StatusOK {
		return fmt.Errorf("GitHub release request failed: %s", res.Status)
	}

	response := releaseResponse{}
	if err := json.NewDecoder(res.Body).Decode(&response); err != nil {
		return fmt.Errorf("error parsing GitHub release: %w", err)
	}

	available := normalizeVersion(response.TagName)
	if !semver.IsValid(available) {
		return fmt.Errorf("invalid NKL release tag: %s", response.TagName)
	}

	comparison := semver.Compare(available, s.version)
	s.logger.Debug().WithFields(log.Fields{
		"comparison": comparison,
		"current":    s.version,
		"available":  available,
	}).Log("Checked NKL GitHub release")

	if comparison == 1 {
		s.logger.Info().WithFields(log.Fields{
			"current":   s.version,
			"available": available,
			"release":   response.HTMLURL,
		}).Log("New NKL version available")
	}

	return nil
}
