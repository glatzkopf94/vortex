#!/bin/sh

set -eu

project_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$project_dir"

. ./release.env

command -v zip >/dev/null 2>&1 || {
    echo "zip wurde nicht gefunden." >&2
    exit 1
}

dist_dir="$project_dir/dist"
package_name="restreamer-nistkastenlivestream-${RELEASE_VERSION}"
stage_dir="$dist_dir/$package_name"
archive="$dist_dir/${package_name}.zip"

mkdir -p "$dist_dir"
if [ -d "$stage_dir" ]; then
    find "$stage_dir" -mindepth 1 -delete
else
    mkdir -p "$stage_dir"
fi
mkdir -p "$stage_dir/tests" "$stage_dir/scripts" "$stage_dir/systemd"

for file in \
    .env.example \
    release.env \
    compose.yaml \
    install.sh \
    status.sh \
    uninstall.sh \
    RELEASE_INSTALL.md \
    CHANGELOG.md \
    RELEASE_NOTES.md \
    TIMELAPSE.md \
    TESTING.md \
    LICENSE \
    NOTICE \
    THIRD_PARTY_NOTICES.md; do
    cp "$file" "$stage_dir/$file"
done
cp tests/smoke-test.sh "$stage_dir/tests/smoke-test.sh"
cp scripts/nkl-update-agent.sh "$stage_dir/scripts/nkl-update-agent.sh"
cp systemd/nkl-restreamer-update.service.in "$stage_dir/systemd/nkl-restreamer-update.service.in"
cp systemd/nkl-restreamer-update.path.in "$stage_dir/systemd/nkl-restreamer-update.path.in"

chmod 0755 \
    "$stage_dir/install.sh" \
    "$stage_dir/status.sh" \
    "$stage_dir/uninstall.sh" \
	"$stage_dir/scripts/nkl-update-agent.sh" \
    "$stage_dir/tests/smoke-test.sh"

rm -f "$archive" "$archive.sha256"
(cd "$dist_dir" && zip -q -r "$(basename "$archive")" "$package_name")
(cd "$dist_dir" && sha256sum "$(basename "$archive")" > "$(basename "$archive").sha256")

echo "$archive"
echo "$archive.sha256"

# Friendly Vortex download plus unchanged legacy package for dev22 UI updates.
vortex_name="vortex-${RELEASE_VERSION}"
rm -rf "$dist_dir/$vortex_name"
cp -a "$stage_dir" "$dist_dir/$vortex_name"
rm -f "$dist_dir/$vortex_name.zip" "$dist_dir/$vortex_name.zip.sha256"
(cd "$dist_dir" && zip -q -r "$vortex_name.zip" "$vortex_name" && sha256sum "$vortex_name.zip" > "$vortex_name.zip.sha256")
echo "$dist_dir/$vortex_name.zip"
