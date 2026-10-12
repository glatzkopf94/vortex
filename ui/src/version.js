// Modified 2026-10-10: Vortex display name; update identifiers preserved.
import pkg from '../package.json';

const Core = '^16.11.0';
const FFmpeg = '^5.1.0 || ^6.1.0 || ^7.0.0 || ^8.1.0 || ^9.0.0';
const UI = pkg.bundle ? pkg.bundle : pkg.name + ' v' + pkg.version;
const Version = pkg.version;
const Product = `Vortex ${pkg.nklVersion || Version}`;
const Repository = 'https://github.com/glatzkopf94/vortex';
const ReleaseAPI = 'https://api.github.com/repos/glatzkopf94/vortex/releases/latest';
const Releases = `${Repository}/releases`;
const Image = 'ghcr.io/glatzkopf94/restreamer-nistkastenlivestream';

export { Core, FFmpeg, UI, Version, Product, Repository, ReleaseAPI, Releases, Image };
