#!env groovy

// Parameters used by this build pipeline.

// You can configure these in the jenkins pipeline job web UI (just add a parameterized build)
// or you can specify these values directly via the pipeline source code, like this:

// properties([parameters([string(defaultValue: 'Hello', description: 'Simple greeting', name: 'Greeting')])])

// BUILD_DISTRO_FLAVOURS
//    type: string
//    defaultValue: x64 xilinx-zynqhf
//    description: Space delimited distro flavours to build in the pipeline.

// SOURCE_MIRROR_URL
//    type: string
//    defaultValue: Empty
//    description: If non-empty check that all sources of built packages are present at SOURCE_MIRROR_URL

// EXPORT_PR_SERVER_JOB
//    type: string
//    defaultValue: Empty
//    description: If non-empty call this job at the end build to save the PR server state

// SSTATE_CACHE_DIR
//    type: string
//    defaultValue: Empty
//    description: Path to sstate-cache directory, possibly on a network share.

// CLEAR_WORKSPACE
//    type: bool
//    defaultValue: false
//    description: If true remove all previous build files before starting a new build.
//                   WARNING: Setting this true will significantly increase build times because the entire contents of
//                            the workspace will be re-created, all git repos re-fetched, etc.

// CLEAR_SSTATE_CACHE
//    type: bool
//    defaultValue: false
//    description: If true remove the build cache before starting
//                   WARNING: It may take a long time to rebuild all distribution binaries not present in the cache

// CLEAR_TMPGLIBC
//    type: bool
//    defaultValue: false
//    description: If true remove the build/tmp-glibc directories; sometimes it's desirable to clean builds without
//                   clearing & rebuilding the whole workspace/sstate triggering long fetches, sstate unarchiving etc.

// ENABLE_SSTATE_CACHE_SNAPSHOT
//    type: bool
//    defaultValue: false
//    description: If true, snapshot the sstate cache at the end of build (caution: will increase archive size a lot)

// ENABLE_BUILD_TAG_PUSH
//    type: bool
//    defaultValue: false
//    description: If true, OE's git kernel build pushes a tag to help identify this build in the kernel git log

// RELEASE_CODENAME
//    type: string
//    defaultValue: oe
//    description: If ENABLE_BUILD_TAG_PUSH is true, this prefix is used to construct the & push the tag identifier

// BUILD_NODE_SLAVE
//    type: string
//    defaultValue: Empty
//    description: Restrict pipeline nodes to run on a specific build slave by name. If this is empty the nodes run
//                   on the default master.

// SSTATE_CACHE_ARCHIVE
//    type: string
//    defaultValue: Empty
//    description: Path to an sstate cache *tar.gz snapshot which will be unpacked into $params.WORKSPACE_DIR/sstate-cache
//                   and re-used across docker container nodes for building NILRT.

// DOCKER_IMAGE_TAG
//    type: string
//    defaultValue: docker-image-${JOB_NAME}
//    description: The pipeline will use the image under this tag for containers building NILRT

// DOCKER_IMAGE_URL
//    type: string
//    defaultValue: Empty
//    description: The pipeline will download and import this image, then use it to build NILRT. If this URL
//                   is specified, it is saved in the archive dir for historical reference.
//                   WARNING: Make sure the image you import was generated with "docker export" and contains the
//                   tag referenced by parameter ${DOCKER_IMAGE_TAG}

// USE_CUSTOM_NI_FEED_JOB
//    type: bool
//    defaultValue: false
//    description: By default the build is configured to fetch NI software feeds from http://download.ni.com
//                   but this can be overriden if, for the sake of build reproducibility, a custom NIFeed job is
//                   supplied (outside NI builds can clone from download.ni.com) containing the NIFeed artifacts

// NI_FEED_JOB_NAME
//    type: string
//    defaultValue: Empty
//    description: The name of the NIFeed job from which to fetch the artifacts

// NI_FEED_ARTIFACT_FILTER
//    type: string
//    defaultValue: objects/export/*
//    description: A filter to use when fetching artifacts from $NI_FEED_JOB_NAME. Default is objects/export/*
//                   because that's a standard path location in NI software builds (you can safely change it).

// NI_RELEASE_BUILD
//    type: boolean
//    defaultValue: false
//    description: Build a final revision of the form x.x.xfx as used by NI software?

// NI_INTERNAL_BUILD
//    type: boolean
//    defaultValue: false
//    description: This build uses internal NI network resources

// NIBUILD_UPDATE_FEEDS_JOB
//    type: string
//    defaultValue: Empty
//    description: Job to trigger for updating the package feed symlink farm after a build has been exported

// NIBUILD_P4_SERVER
//    type: string
//    defaultValue: Empty
//    description: Internal NI perforce server hostname

// NIBUILD_COMPONENT_PATH
//    type: string
//    defaultValue: Empty
//    description: NI internal component name used for build artifact archive storage

// NIBUILD_ENV_SCRIPT_PATH
//    type: string
//    defaultValue: Empty
//    description: Script used to initialize nibuild environment (credentials, p4 clientspec etc)

// NIBUILD_MNT_BALTIC
//    type: string
//    defaultValue: /mnt/baltic/
//    description: Full path to the local mount location of NI's //baltic/ server

// NIBUILD_MNT_NIRVANA
//    type: string
//    defaultValue: /mnt/nirvana/
//    description: Full path to the local mount location of NI's //nirvana/ server

// NIBUILD_PACKAGE_INDEX_SIGNING_URL
//    type: string
//    defaultValue: Empty
//    description: SSH connection string (E.g. user@host.domain) to nibuild compatible
//                 signing service. If defined, signs package index files.

// NIBUILD_PACKAGE_INDEX_SIGNING_KEY
//    type: string
//    defaultValue: Empty
//    description: Name/ID of key residing on aforementioned nibuild compatible
//                 signing service.

// ENABLE_TESTING
//    type: boolean
//    defaultValue: True
//    description: If True, run the image test stages and store their results
//                 in the archive; else, skip these stages.

node (params.BUILD_NODE_SLAVE) {
    def archive_dir = "${workspace}/archive"
    def nifeeds_dir = "${workspace}/nifeeds"
    def sstate_cache_dir = "${workspace}/sstate-cache"

    if (params.SSTATE_CACHE_DIR) {
        sstate_cache_dir = "${params.SSTATE_CACHE_DIR}"
    }

    // print env vars for easy reference in the build log
    echo sh(returnStdout: true, script: 'env')

    if (params.CLEAR_WORKSPACE) {
        stage("Clearing entire workspace") {
            sh "rm -rf ${workspace}; mkdir -p ${workspace}"
        }
    }

    stage("Fetching git sources") {
        checkout scm
        sh 'git submodule init'
        // The --remote flag will be removed once we'll have a functioning autoci branch
        sh 'git submodule update --remote --checkout'
    }

    // unconditionally clear the archive (each build recreates it from scratch)
    stage("Clearing archive dir") {
        sh "rm -rf ${archive_dir}; mkdir -vp ${archive_dir}"
    }

    if (params.DOCKER_IMAGE_URL) {
        stage("Importing docker image") {
            sh "curl -s ${params.DOCKER_IMAGE_URL} -o docker-image.tar"
            sh "docker load -i docker-image.tar"
            sh "docker container prune -f"
            sh "docker image prune -f"
            sh "echo ${params.DOCKER_IMAGE_URL} > $archive_dir/dockerImageURL.txt"
        }
    }

    sh "docker images | grep -E \"^${params.DOCKER_IMAGE_TAG}.*latest\" | awk -e '{print \$3}' > $archive_dir/dockerImageHash.txt"

    stage("Initializing sstate cache") {
        if (params.CLEAR_SSTATE_CACHE) {
            sh "rm -rf ${sstate_cache_dir}"
        }
        sh "install -v --owner=jenkins --group=jenkins -d ${sstate_cache_dir}"
    }

    if (params.SSTATE_CACHE_ARCHIVE) {
        stage("Unpacking sstate-cache archive") {
            sh "mkdir -p $sstate_cache_dir"
            sh "tar --overwrite -xf ${params.SSTATE_CACHE_ARCHIVE} -C $sstate_cache_dir -I pigz"
        }
    }

    if (params.USE_CUSTOM_NI_FEED_JOB) {
        stage("Unpacking NIFeeds") {
            sh "rm -rf $nifeeds_dir && mkdir -p $nifeeds_dir"

            step ([$class: 'CopyArtifact',
                   projectName: params.NI_FEED_JOB_NAME,
                   filter: params.NI_FEED_ARTIFACT_FILTER,
                   target: "$nifeeds_dir"])

            sh "cp $nifeeds_dir/objects/export/bsExportP4Path.txt $archive_dir/bsExportP4PathNIFeed.txt"

            sh "tar -xf $nifeeds_dir/objects/export/feeds.tar.gz -C $nifeeds_dir"
        }
    }

    if (params.NI_INTERNAL_BUILD) {
        stage("Initializing nibuild component") {
            sh """#!/bin/bash
                  source ${params.NIBUILD_ENV_SCRIPT_PATH}
                  mkdir -p ${params.NIBUILD_COMPONENT_PATH}
                  cd ${params.NIBUILD_COMPONENT_PATH}
                  p4 sync ...
               """
            sh "grep -oP '(?<=version = )[0-9dabf.]+(?=;)' ${params.NIBUILD_COMPONENT_PATH}/package \
                    | tee $archive_dir/bsExportVersionNumb.txt"
        }
    }

    def build_targets = params.BUILD_DISTRO_FLAVOURS.tokenize()

    // We must mount /etc/passwd and /etc/groups here to allow git to resolve
    // the uid to a valid user.
    // We must create a tmpfs in ~/.config for VBoxManager to store temporary
    // files.
    docker.image(params.DOCKER_IMAGE_TAG).inside("\
                    --mount type=tmpfs,destination=${env.HOME},tmpfs-mode=0777 \
                    -v ${env.HOME}/.ssh:${env.HOME}/.ssh \
                    --mount type=tmpfs,destination=${env.HOME}/.config,tmpfs-mode=0777 \
                    --mount type=tmpfs,destination=${env.HOME}/.ccache,tmpfs-mode=0777 \
                    -v /etc/passwd:/etc/passwd:ro \
                    -v /etc/group:/etc/group:ro \
                    -v ${workspace}:/mnt/workspace \
                    -v ${sstate_cache_dir}:/mnt/sstate-cache \
                    -v ${NIBUILD_MNT_NIRVANA}:/mnt/nirvana \
                    -v ${NIBUILD_MNT_BALTIC}:/mnt/baltic") {

            def distro_flavour_builds = [:]
            for (int i = 0; i < build_targets.size(); i++) {
                def distro_flavour = build_targets.get(i)

                distro_flavour_builds["$distro_flavour"] = {
                    withEnv(["MACHINE=$distro_flavour"]) {

                        def node_sstate_cache_dir = "/mnt/sstate-cache"
                        def build_dir             = "/mnt/workspace/build_${env.MACHINE}"
                        def node_archive_dir      = "/mnt/workspace/archive"
                        def archive_img_path      = "$node_archive_dir/images/NILinuxRT-$distro_flavour"
                        def feed_dir              = "$node_archive_dir/feeds/NILinuxRT-$distro_flavour"

                        def distro_flav_build_tag = "${params.RELEASE_CODENAME}-${distro_flavour}-${env.BUILD_NUMBER}"
                        if (params.NI_INTERNAL_BUILD) {
                            def bs_export = sh(script: "cat $node_archive_dir/bsExportVersionNumb.txt", returnStdout: true).trim()
                            distro_flav_build_tag = "${params.RELEASE_CODENAME}-${bs_export}-${distro_flavour}-${env.BUILD_NUMBER}"
                        }

                        sh "mkdir -p $feed_dir"
                        sh "mkdir -p $archive_img_path"

                        stage("$distro_flavour initializing bitbake environment") {
                            // always clear to be sure previous builds don't pollute the current one
                            sh "rm -rf $build_dir/conf/auto.conf \
                                $build_dir/bitbake.stdout.txt \
                                $build_dir/xunit-results.xml \
                                buildVM-working-dir \
                                wic-temp-output-dir"

                            if (params.CLEAR_TMPGLIBC) {
                                sh "rm -rf $build_dir/tmp-glibc"
                            }

                            // mkdir to avoid broken symlink if no sstate cache was given (first build from scratch)
                            sh "mkdir -p $build_dir/conf $node_sstate_cache_dir"
                            sh "rm -rf $build_dir/sstate-cache"
                            sh "ln -sf $node_sstate_cache_dir $build_dir/sstate-cache"

                            if (params.USE_CUSTOM_NI_FEED_JOB) {
                                // configure OE to pull ipks from NIFeeds
                                def nisubfeed_path="/mnt/workspace/nifeeds/feeds/NILinuxRT-${distro_flavour}"
                                sh "echo 'IPK_NI_SUBFEED_URI = \"file://$nisubfeed_path\"' >> $build_dir/conf/auto.conf"
                            }

                            sh "echo 'BUILDNAME = \"${distro_flav_build_tag}\"' >> $build_dir/conf/auto.conf"

                            if (params.ENABLE_BUILD_TAG_PUSH) {
                                sh "echo 'ENABLE_BUILD_TAG_PUSH = \"Yes\"' >> $build_dir/conf/auto.conf"
                            }
                        }

                        stage("$distro_flavour archiving bitbake environment") {
                            sh "git rev-parse HEAD > $node_archive_dir/nilrt-gitCommitId-${distro_flavour}.txt"
                            sh "git submodule status --recursive > $node_archive_dir/nilrt-git-submodule-status-${distro_flavour}.txt"

                            sh "set > $node_archive_dir/env-${distro_flavour}.txt"

                            sh """#!/bin/bash
                                  set -e -o pipefail
                                  . ./ni-oe-init-build-env $build_dir
                                  bitbake -e > $node_archive_dir/buildEnv-${distro_flavour}.txt
                               """
                        }

                        stage("$distro_flavour core feed") {
                            sh """#!/bin/bash
                                  set -e -o pipefail

                                  . ./ni-oe-init-build-env $build_dir

                                  rm -rf tmp-glibc/deploy/ipk
                                  mkdir -p tmp-glibc/deploy/ipk-core
                                  ln -s \$PWD/tmp-glibc/deploy/ipk-core tmp-glibc/deploy/ipk

                                  bitbake packagegroup-ni-coreimagerepo 2>&1 | tee bitbake.stdout.txt
                                  # Create the core feed package index for use by the image build steps
                                  bitbake package-index 2>&1 | tee -a bitbake.stdout.txt
                               """
                        }

                        stage("$distro_flavour images") {
                            sh """#!/bin/bash
                                  set -e -o pipefail

                                  . ./ni-oe-init-build-env $build_dir

                                  # Bitbake doesn't do a good job at detecting changes that require a image
                                  # rebuild, when BUILD_FROM_FEEDS is used. Clean to always rebuild.
                                  # NOTE: If the sstate cache is shared, this stage will need a lock to
                                  #       avoid a race condition between cleanning/building.
                                  bitbake -ccleanall \
                                        minimal-nilrt-image \
                                        minimal-nilrt-ptest-image \
                                    2>&1 | tee -a bitbake.stdout.txt

                                  bitbake \
                                        minimal-nilrt-image \
                                        minimal-nilrt-ptest-image \
                                    2>&1 | tee -a bitbake.stdout.txt

                                  # Only for x64 because we don't have ARM ISO images
                                  if [ $distro_flavour == 'x64' ]; then
                                      # Bitbake doesn't do a good job at detecting changes that require a image
                                      # rebuild, when BUILD_FROM_FEEDS is used. Clean to always rebuild.
                                      # NOTE: If the sstate cache is shared, this stage will need a lock to
                                      #       avoid a race condition between cleanning/building.
                                      bitbake -ccleanall \
                                            minimal-nilrt-bundle-image \
                                            minimal-nilrt-bundle \
                                            nilrt-initramfs \
                                            init-restore-mode \
                                            safemode-restore-image \
                                            restore-mode-image \
                                        2>&1 | tee -a bitbake.stdout.txt

                                      bitbake \
                                            minimal-nilrt-ptest-image \
                                            safemode-restore-image \
                                            restore-mode-image \
                                        2>&1 | tee -a bitbake.stdout.txt

                                      ../scripts/buildVM.sh -d 10240 -m 1024 -n nilrt-vm -r restore-mode-image
                                  fi
                               """

                            // we don't have provisioning images for NXG ARM like we have ISOs for x64, nor VMs
                            if (distro_flavour == 'x64') {
                                sh "cp -L $build_dir/tmp-glibc/deploy/images/$distro_flavour/restore-mode-image-${distro_flavour}.iso \
                                    $archive_img_path/restore-mode-image-${distro_flavour}.iso"
                                sh "cp -L $build_dir/tmp-glibc/deploy/images/$distro_flavour/safemode-restore-image-${distro_flavour}.iso \
                                    $archive_img_path/safemode-restore-image-${distro_flavour}.iso"

                                sh "cp -L $build_dir/tmp-glibc/deploy/images/$distro_flavour/nilrt-vm-$distro_flavour-virtualbox.zip $archive_img_path"
                                sh "cp -L $build_dir/tmp-glibc/deploy/images/$distro_flavour/nilrt-vm-$distro_flavour-vmware.zip $archive_img_path"
                                sh "cp -L $build_dir/tmp-glibc/deploy/images/$distro_flavour/nilrt-vm-$distro_flavour-hyperv.zip $archive_img_path"
                                sh "cp -L $build_dir/tmp-glibc/deploy/images/$distro_flavour/nilrt-vm-$distro_flavour-qemu.zip $archive_img_path"
                            }

                            if (distro_flavour == 'xilinx-zynqhf') {
                                // cpio.gz.u-boot is a ramdisk present only for xilinx-zynqhf
                                sh "cp -L $build_dir/tmp-glibc/deploy/images/$distro_flavour/restore-mode-image-${distro_flavour}.cpio.gz.u-boot \
                                          $archive_img_path/restore-mode-image-${distro_flavour}.cpio.gz.u-boot"
                            }

                            sh "cp -L $build_dir/tmp-glibc/deploy/images/$distro_flavour/minimal-nilrt-image-${distro_flavour}.tar.bz2 \
                                  $archive_img_path/minimal-nilrt-image-${distro_flavour}.tar.bz2"
                            sh "cp -L $build_dir/tmp-glibc/deploy/images/$distro_flavour/minimal-nilrt-ptest-image-${distro_flavour}.tar.bz2 \
                                  $archive_img_path/minimal-nilrt-ptest-image-${distro_flavour}.tar.bz2"

                            sh "cp -L $build_dir/tmp-glibc/deploy/images/$distro_flavour/minimal-nilrt-image-${distro_flavour}.ext2 \
                                  $archive_img_path/minimal-nilrt-image-${distro_flavour}.ext2"
                            sh "cp -L $build_dir/tmp-glibc/deploy/images/$distro_flavour/minimal-nilrt-ptest-image-${distro_flavour}.ext2 \
                                  $archive_img_path/minimal-nilrt-ptest-image-${distro_flavour}.ext2"
                        }

                        // The dist feed stage must be run immediately after the images stage.
                        // The dist recipes require packages from the core feed and the deploy/images.
                        stage("$distro_flavour dist feed") {
                            sh """#!/bin/bash
                                  set -e -o pipefail

                                  . ./ni-oe-init-build-env $build_dir

                                  dist_recipes=" \
                                      dist-nilrt-grub-gateway \
                                      dist-nilrt-efi-ab \
                                      dist-nilrt-efi-ab-gateway \
                                  "

                                  bitbake \$dist_recipes

                                  # move created recipe ipks to their own dist feed
                                  rm -rf   ./tmp-glibc/deploy/ipk-dist
                                  mkdir -p ./tmp-glibc/deploy/ipk-dist
                                  for dist_recipe in \$dist_recipes; do
                                      dep_ipk_path=`find ./tmp-glibc/work -type d -path "./tmp-glibc/work/*/\$dist_recipe/*/deploy-ipks"`
                                      echo DEBUG: "\$dist_recipe => \$dep_ipk_path"
                                      dep_ipks=`find "\$dep_ipk_path" -name "*.ipk" -printf "%P "`
                                      for dep_ipk in \$dep_ipks; do
                                          echo "DEP_IPK \$dep_ipk"
                                          install -vD "./tmp-glibc/deploy/ipk/\$dep_ipk" "./tmp-glibc/deploy/ipk-dist/\$dep_ipk"
                                          rm -v "./tmp-glibc/deploy/ipk/\$dep_ipk"
                                      done
                                  done
                               """
                        }

                        stage("$distro_flavour extras feed") {
                            sh """#!/bin/bash
                                  set -e -o pipefail

                                  . ./ni-oe-init-build-env $build_dir

                                  # Both the desirable and extra packagegroups should be deposited into the
                                  # "extra" feed.
                                  rm -rf tmp-glibc/deploy/ipk
                                  mkdir -p tmp-glibc/deploy/ipk-extra
                                  ln -s \$PWD/tmp-glibc/deploy/ipk-extra tmp-glibc/deploy/ipk

                                  echo "Building desirable packages..."
                                  bitbake packagegroup-ni-desirable 2>&1 | tee -a bitbake.stdout.txt

                                  echo "Building extra packages..."
                                  bitbake --continue packagegroup-ni-extra 2>&1 | tee -a bitbake.stdout.txt || true

                                  # make sure no main/core feed ipk exists in the extras feed
                                  ipk_paths=`find ./tmp-glibc/deploy/ipk-core -name *.ipk | rev | cut -d"/" -f1-2 | rev`
                                  for ipk_file in \$ipk_paths; do
                                      rm -fv tmp-glibc/deploy/ipk/\$ipk_file
                                  done;
                              """
                        }

                        stage("$distro_flavour feed finalization") {
                            sh """#!/bin/bash
                                  set -e -o pipefail

                                  . ./ni-oe-init-build-env $build_dir

                                  feeds=" \
                                      core \
                                      dist \
                                      extra \
                                  "

                                  for feed in \$feeds; do
                                      echo "Finalizing \$feed feed..."
                                      # (Re)create package indexes
                                      rm -f "./tmp-glibc/deploy/ipk"
                                      ln -s "\$PWD/tmp-glibc/deploy/ipk-\${feed}" "./tmp-glibc/deploy/ipk"
                                      bitbake package-index 2>&1 | tee -a bitbake.stdout.txt

                                      # Sign the feed indexes
                                      if [ -n "${params.NIBUILD_PACKAGE_INDEX_SIGNING_URL}" ]; then
                                          ../scripts/jenkins/sign-feed-index.sh \
                                              "${params.NIBUILD_PACKAGE_INDEX_SIGNING_URL}" \
                                              "${params.NIBUILD_PACKAGE_INDEX_SIGNING_KEY}" \
                                              "NIOE-Pipeline ${distro_flav_build_tag} ${distro_flavour} \$feed" \
                                              "./tmp-glibc/deploy/ipk"
                                      fi

                                      # Copy feeds to the export directory
                                  done

                                  cp -Lr $build_dir/tmp-glibc/deploy/ipk-core  -T $feed_dir/main
                                  cp -Lr $build_dir/tmp-glibc/deploy/ipk-dist  -T $feed_dir/dist
                                  cp -Lr $build_dir/tmp-glibc/deploy/ipk-extra -T $feed_dir/extra

                               """
                        } // stage

                        // a feed package morgue is created because metadata is invalidated without invalidating sstate
                        // (it's reused in a new package revision) but because PR server state is updated only at the end
                        // of a build, packages in this situation will continue to clobber older revisions until the PR
                        // state is updated. Since in 99% of occuring cases this is intentional (updating recipes) and
                        // clobbered packages are identical except for minor metadata changes, note and remove the morgues.
                        sh """#!/bin/bash
                              MORGUES=\$(find $feed_dir -type d -name morgue)
                              if [ \$(echo "\$MORGUES" | wc -w) -ne 0 ]; then
                                  echo "\$MORGUES" | while read morgue; do
                                      echo "WARNING: Package morgue detected:"
                                      find \$morgue
                                      rm -rf \$morgue
                                  done
                              fi
                           """

                        sh "scripts/jenkins/create-xunit-error-xml.sh $build_dir/bitbake.stdout.txt $build_dir/xunit-results.xml"

                        sh "tar cf $node_archive_dir/buildhistory-${distro_flavour}.tar.gz $build_dir/buildhistory/ -I pigz"

                        // check at the end of build to ensure we verify all OE downloaded packages
                        if (params.SOURCE_MIRROR_URL) {
                            sh "MIRROR_URL=$params.SOURCE_MIRROR_URL DOWNLOAD_DIR=$build_dir/downloads scripts/jenkins/test-source-mirror.py"
                        }
                    } // withEnv
                } // distro_flavour_builds
            } // for

            parallel distro_flavour_builds

        } // container.inside

    if (params.EXPORT_PR_SERVER_JOB) {
        build(job: params.EXPORT_PR_SERVER_JOB, propagate: true)
    }

    for (int i = 0; i < build_targets.size(); i++) {
        def distro_flavour = build_targets.get(i)
        step([$class: "JUnitResultArchiver", testResults: "build_$distro_flavour/xunit-results.xml"])
    }

// The archive under ${workspace}/archive has the following structure
// TODO: In the future we want to remove the $distro_flavour separation boundry from the feeds
// archive/
// ├── buildEnv-$distro_flavour.txt
// ├── buildhistory-$distro_flavour.tar.gz
// ├── bsExportP4Path.txt
// ├── bsExportP4PathNIFeed.txt
// ├── bsExportVersionNumb.txt
// ├── env-$distro_flavour.txt
// ├── feeds
// │   ├── NILinuxRT-$distro_flavour
// │   │   ├── main
// │   │   ├── images
// │   │   └── extra
// ├── images
// │   ├── NILinuxRT-$distro_flavour
// │   └── ...
// ├── nifeeds-bsExportP4Path.txt
// ├── nilrt-gitCommitId.txt
// ├── nilrt-git-submodule-status.txt
// ├── sstate-cache.tar.gz
// ├── dockerImageURL.txt
// └── dockerImageHash.txt

    // PHASE: TESTING
    if (params.ENABLE_TESTING) {
        stage('Testing') {
            if (!build_targets.contains('x64')) {
                echo("Skipping testing phase because x64 images were not built.")
                return // quits the wrapping stage
            }

            def test_dir = "${archive_dir}/tests"
            dir(test_dir) {
                // Provisioning Test
                sh(script: """#!/bin/bash
                              set -exo pipefail
                              source /etc/profile
                              export LIBGUESTFS_DEBUG=1 LIBGUESTFS_TRACE=1
                              ${workspace}/scripts/provisioningTest.sh -p ${archive_dir}/images/NILinuxRT-x64 2>&1 | \
                              tee ./provisioning.log
                           """,
                   returnStdout: true,
                   label: "Test - Provisioning")
            }
        }
    }

    if (params.ENABLE_SSTATE_CACHE_SNAPSHOT || params.NI_RELEASE_BUILD) {
        stage("Packing sstate cache") {
            sh "tar cf ${workspace}/archive/sstate-cache.tar.gz ${workspace}/sstate-cache -I pigz"
        }
    }

    if (params.NI_INTERNAL_BUILD) {
        stage("Exporting build") {

            // sanity check that parallel nodes built the same sources then clobber identical files (containing machine names)
            sh "md5sum $archive_dir/nilrt-gitCommitId*.txt | awk 'NR>1&&\$1!=last{exit 1}{last=\$1}' && \
                    for file in $archive_dir/nilrt-gitCommitId*.txt; do \
                        mv \$file $archive_dir/nilrt-gitCommitId.txt; \
                    done"
            sh "md5sum $archive_dir/nilrt-git-submodule-status*.txt | awk 'NR>1&&\$1!=last{exit 1}{last=\$1}' && \
                    for file in $archive_dir/nilrt-git-submodule-status*.txt; do \
                        mv \$file $archive_dir/nilrt-git-submodule-status.txt; \
                    done"

            // sanity check feeds (all important files are present and there are no duplicate ipks)
            sh """#!/bin/bash -xe
                  for dir in $archive_dir/feeds/NILinuxRT-*/* ; do
                      pushd \$dir

                      # assert feeds have expected subfeeds
                      if [ `basename "\$dir"` = "dist" ]; then
                          [ -d "core2-64" ]
                      else
                          [ -d "all" ]
                          [ -d 'cortexa9hf-vfpv3' -a -d 'xilinx-zynqhf' ] || \
                          [ -d 'core2-64' -a -d 'x64' ]
                      fi

                      # assert all subfeeds have package indexes
                      for subFeedDir in `find . -type d`; do
                          [ -f "\$subFeedDir/Packages" ]
                          if [ '.' != "\$subFeedDir" ]; then
                              [ -f "\$subFeedDir/Packages.gz" ]
                              [ -f "\$subFeedDir/Packages.stamps" ]
                          fi
                      done

                      popd
                  done

                  # search for duplicates by verifying the full path because we expect some file names to be duplicated
                  # like the Packages(.gz) and allarch ipk's between machines
                  [ `find $archive_dir/feeds -name '*.ipk' | wc -l` -eq \
                    `find $archive_dir/feeds -name '*.ipk' | sort | uniq | wc -l` ]
               """

            sh """#!/bin/bash
                  source ${params.NIBUILD_ENV_SCRIPT_PATH}
                  cd ${params.NIBUILD_COMPONENT_PATH}
                  source ./setupEnv.sh
                  submitExport --yes --revert >/dev/null 2>&1 || echo 'No existing export to revert'
                  ARCHIVE_DIR="$archive_dir" buildExport --yes --nodistribution
                  submitExport --yes --submit
                  rm -f buildExport*log* submitExport*log*
               """

            if (params.NIBUILD_UPDATE_FEEDS_JOB) {
                build(job: params.NIBUILD_UPDATE_FEEDS_JOB, propagate: true)
            }
        }
    }
}
