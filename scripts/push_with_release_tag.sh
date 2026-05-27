#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 <tag>"
  echo
  echo "Examples:"
  echo "  $0 1.0.0"
  echo "  $0 v1.0.0"
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "$#" -ne 1 ]]; then
  usage >&2
  exit 64
fi

tag="$1"
if [[ "$tag" != v* ]]; then
  tag="v${tag}"
fi

if [[ ! "$tag" =~ ^v[0-9]+[.][0-9]+[.][0-9]+([.-][0-9A-Za-z.-]+)?$ ]]; then
  echo "error: tag must look like v1.0.0 or 1.0.0; got '$1'" >&2
  exit 64
fi

git rev-parse --is-inside-work-tree >/dev/null

remote="${RELEASE_REMOTE:-origin}"
branch="$(git symbolic-ref --quiet --short HEAD)" || {
  echo "error: not on a branch; checkout the branch you want to release first" >&2
  exit 1
}

head_commit="$(git rev-parse HEAD)"

if git rev-parse --quiet --verify "refs/tags/${tag}" >/dev/null; then
  tag_commit="$(git rev-list -n 1 "${tag}")"
  if [[ "$tag_commit" != "$head_commit" ]]; then
    echo "error: local tag '${tag}' already points to ${tag_commit}, not HEAD ${head_commit}" >&2
    exit 1
  fi
  echo "Tag ${tag} already exists locally on HEAD."
else
  git tag -a "${tag}" -m "${tag}"
  echo "Created tag ${tag} on ${head_commit}."
fi

echo "Pushing branch ${branch} to ${remote}..."
git push "${remote}" "${branch}"

echo "Pushing tag ${tag} to ${remote}..."
git push "${remote}" "${tag}"
