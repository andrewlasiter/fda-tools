#!/usr/bin/env bash
# FDA Tools - Docker Build Script
# Builds the FDA Tools container image with configurable options
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Defaults
IMAGE_NAME="${FDA_IMAGE_NAME:-fda-tools}"
VERSION="${FDA_VERSION:-$(python3 -c "import tomllib; print(tomllib.load(open('$ROOT_DIR/pyproject.toml','rb'))['project']['version'])" 2>/dev/null || echo "latest")}"
ENVIRONMENT="${ENVIRONMENT:-production}"
ENABLE_OPTIONAL_DEPS="${ENABLE_OPTIONAL_DEPS:-true}"
PLATFORM="${PLATFORM:-linux/amd64}"
PUSH="${PUSH:-false}"
REGISTRY="${REGISTRY:-}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Build the FDA Tools Docker image.

Options:
  -v, --version VERSION     Image version tag (default: from pyproject.toml)
  -e, --environment ENV     Build environment: production|development (default: production)
  --no-optional             Skip optional dependencies (smaller image)
  --push                    Push image to registry after build
  --registry REGISTRY       Container registry prefix (e.g., ghcr.io/myorg)
  --platform PLATFORM       Target platform (default: linux/amd64)
  -h, --help                Show this help message

Examples:
  $(basename "$0")                          # Build production image
  $(basename "$0") -v 5.37.0               # Build specific version
  $(basename "$0") -e development           # Build development image
  $(basename "$0") --push --registry ghcr.io/myorg  # Build and push
EOF
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version) VERSION="$2"; shift 2 ;;
        -e|--environment) ENVIRONMENT="$2"; shift 2 ;;
        --no-optional) ENABLE_OPTIONAL_DEPS="false"; shift ;;
        --push) PUSH="true"; shift ;;
        --registry) REGISTRY="$2"; shift 2 ;;
        --platform) PLATFORM="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# Build the full image tag
TAG="${IMAGE_NAME}:${VERSION}"
if [[ -n "$REGISTRY" ]]; then
    TAG="${REGISTRY}/${TAG}"
fi
LATEST_TAG="${TAG%:*}:latest"

echo "Building FDA Tools Docker image..."
echo "  Image:       $TAG"
echo "  Environment: $ENVIRONMENT"
echo "  Optional:    $ENABLE_OPTIONAL_DEPS"
echo "  Platform:    $PLATFORM"

cd "$ROOT_DIR"

docker build \
    --platform "$PLATFORM" \
    --build-arg "PYTHON_VERSION=3.11" \
    --build-arg "ENVIRONMENT=$ENVIRONMENT" \
    --build-arg "ENABLE_OPTIONAL_DEPS=$ENABLE_OPTIONAL_DEPS" \
    --tag "$TAG" \
    --tag "$LATEST_TAG" \
    --file Dockerfile \
    .

echo ""
echo "Build complete: $TAG"

if [[ "$PUSH" == "true" ]]; then
    echo "Pushing $TAG..."
    docker push "$TAG"
    docker push "$LATEST_TAG"
    echo "Pushed: $TAG"
fi
