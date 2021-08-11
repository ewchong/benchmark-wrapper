#!/bin/bash

set -x

source ci/common.sh

# Build image for ci
image_spec=$SNAFU_WRAPPER_IMAGE_PREFIX/coremark-pro:$SNAFU_IMAGE_TAG
build_and_push snafu/coremarkpro/Dockerfile $image_spec
pushd ripsaw
source tests/test_coremarkpro.sh
