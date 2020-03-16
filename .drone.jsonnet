local PythonVersion(pyversion='3.5') = {
  name: 'python' + std.strReplace(pyversion, '.', '') + '-pytest',
  image: 'python:' + pyversion,
  environment: {
    PY_COLORS: 1,
    SETUPTOOLS_SCM_PRETEND_VERSION: '${DRONE_TAG##v}',
  },
  commands: [
    'pip install -qq .',
    'docker-tidy --help',
    'docker-tidy --version',
  ],
  depends_on: [
    'clone',
  ],
};

local PipelineLint = {
  kind: 'pipeline',
  name: 'lint',
  platform: {
    os: 'linux',
    arch: 'amd64',
  },
  steps: [
    {
      name: 'flake8',
      image: 'python:3.7',
      environment: {
        PY_COLORS: 1,
      },
      commands: [
        'pip install pipenv -qq',
        'pipenv --bare install --dev --keep-outdated',
        'pipenv run flake8 ./dockertidy',
      ],
    },
  ],
  trigger: {
    ref: ['refs/heads/master', 'refs/tags/**', 'refs/pull/**'],
  },
};

local PipelineDeps = {
  kind: 'pipeline',
  name: 'dependencies',
  platform: {
    os: 'linux',
    arch: 'amd64',
  },
  steps: [
    {
      name: 'pipenv',
      image: 'python:3.7',
      environment: {
        PY_COLORS: 1,
      },
      commands: [
        'pip install pipenv -qq',
        'pipenv --bare install --keep-outdated',
        'pipenv check -i 37752',
        'pipenv --bare install --dev --keep-outdated',
        'pipenv run pipenv-setup check',
      ],
    },
  ],
  depends_on: [
    'lint',
  ],
  trigger: {
    ref: ['refs/heads/master', 'refs/tags/**', 'refs/pull/**'],
  },
};

local PipelineTest = {
  kind: 'pipeline',
  name: 'test',
  platform: {
    os: 'linux',
    arch: 'amd64',
  },
  steps: [
    {
      name: 'pytest',
      image: 'python:3.8',
      environment: {
        PY_COLORS: 1,
      },
      commands: [
        'pip install pipenv -qq',
        'pipenv --bare install --dev --keep-outdated',
        'pipenv run pytest dockertidy/tests/ --cov=dockertidy/ --no-cov-on-fail',
      ],
    },
    {
      name: 'codecov',
      image: 'python:3.8',
      environment: {
        PY_COLORS: 1,
        CODECOV_TOKEN: { from_secret: 'codecov_token' },
      },
      commands: [
        'pip install codecov',
        'codecov --required',
      ],
    },
  ],
  depends_on: [
    'dependencies',
  ],
  trigger: {
    ref: ['refs/heads/master', 'refs/tags/**', 'refs/pull/**'],
  },
};

local PipelineVerify = {
  kind: 'pipeline',
  name: 'verify',
  platform: {
    os: 'linux',
    arch: 'amd64',
  },
  steps: [
    PythonVersion(pyversion='3.5'),
    PythonVersion(pyversion='3.6'),
    PythonVersion(pyversion='3.7'),
    PythonVersion(pyversion='3.8'),
  ],
  depends_on: [
    'test',
  ],
  trigger: {
    ref: ['refs/heads/master', 'refs/tags/**', 'refs/pull/**'],
  },
};

local PipelineSecurity = {
  kind: 'pipeline',
  name: 'security',
  platform: {
    os: 'linux',
    arch: 'amd64',
  },
  steps: [
    {
      name: 'bandit',
      image: 'python:3.7',
      environment: {
        PY_COLORS: 1,
      },
      commands: [
        'pip install pipenv -qq',
        'pipenv --bare install --dev --keep-outdated',
        'pipenv run bandit -r ./dockertidy -x ./dockertidy/tests',
      ],
    },
  ],
  depends_on: [
    'verify',
  ],
  trigger: {
    ref: ['refs/heads/master', 'refs/tags/**', 'refs/pull/**'],
  },
};

local PipelineBuildPackage = {
  kind: 'pipeline',
  name: 'build-package',
  platform: {
    os: 'linux',
    arch: 'amd64',
  },
  steps: [
    {
      name: 'build',
      image: 'python:3.7',
      environment: {
        SETUPTOOLS_SCM_PRETEND_VERSION: '${DRONE_TAG##v}',
      },
      commands: [
        'python setup.py sdist bdist_wheel',
      ],
    },
    {
      name: 'checksum',
      image: 'alpine',
      commands: [
        'cd dist/ && sha256sum * > ../sha256sum.txt',
      ],
    },
    {
      name: 'publish-github',
      image: 'plugins/github-release',
      settings: {
        overwrite: true,
        api_key: { from_secret: 'github_token' },
        files: ['dist/*', 'sha256sum.txt'],
        title: '${DRONE_TAG}',
        note: 'CHANGELOG.md',
      },
      when: {
        ref: ['refs/tags/**'],
      },
    },
    {
      name: 'publish-pypi',
      image: 'plugins/pypi',
      settings: {
        username: { from_secret: 'pypi_username' },
        password: { from_secret: 'pypi_password' },
        repository: 'https://upload.pypi.org/legacy/',
        skip_build: true,
      },
      when: {
        ref: ['refs/tags/**'],
      },
    },
  ],
  depends_on: [
    'security',
  ],
  trigger: {
    ref: ['refs/heads/master', 'refs/tags/**', 'refs/pull/**'],
  },
};

local PipelineBuildContainer(arch='amd64') = {
  kind: 'pipeline',
  name: 'build-container-' + arch,
  platform: {
    os: 'linux',
    arch: arch,
  },
  steps: [
    {
      name: 'build',
      image: 'python:3.7',
      commands: [
        'python setup.py bdist_wheel',
      ],
      environment: {
        SETUPTOOLS_SCM_PRETEND_VERSION: '${DRONE_TAG##v}',
      },
    },
    {
      name: 'dryrun',
      image: 'plugins/docker:18-linux-' + arch,
      settings: {
        dry_run: true,
        dockerfile: 'Dockerfile',
        repo: 'xoxys/${DRONE_REPO_NAME}',
        username: { from_secret: 'docker_username' },
        password: { from_secret: 'docker_password' },
      },
      when: {
        ref: ['refs/pull/**'],
      },
    },
    {
      name: 'publish',
      image: 'plugins/docker:18-linux-' + arch,
      settings: {
        auto_tag: true,
        auto_tag_suffix: arch,
        dockerfile: 'Dockerfile',
        repo: 'xoxys/${DRONE_REPO_NAME}',
        username: { from_secret: 'docker_username' },
        password: { from_secret: 'docker_password' },
      },
      when: {
        ref: ['refs/heads/master', 'refs/tags/**'],
      },
    },
  ],
  depends_on: [
    'security',
  ],
  trigger: {
    ref: ['refs/heads/master', 'refs/tags/**', 'refs/pull/**'],
  },
};

local PipelineDocs = {
  kind: 'pipeline',
  name: 'docs',
  platform: {
    os: 'linux',
    arch: 'amd64',
  },
  concurrency: {
    limit: 1,
  },
  steps: [
    {
      name: 'assets',
      image: 'byrnedo/alpine-curl',
      commands: [
        'mkdir -p docs/themes/hugo-geekdoc/',
        'curl -L https://github.com/xoxys/hugo-geekdoc/releases/latest/download/hugo-geekdoc.tar.gz | tar -xz -C docs/themes/hugo-geekdoc/ --strip-components=1',
      ],
    },
    {
      name: 'test',
      image: 'klakegg/hugo:0.59.1-ext-alpine',
      commands: [
        'cd docs/ && hugo-official',
      ],
    },
    {
      name: 'freeze',
      image: 'appleboy/drone-ssh:1.5.5',
      settings: {
        host: { from_secret: 'ssh_host' },
        key: { from_secret: 'ssh_key' },
        script: [
          'cp -R /var/www/virtual/geeklab/html/docker-tidy.geekdocs.de/ /var/www/virtual/geeklab/html/dockertidy_freeze/',
          'ln -sfn /var/www/virtual/geeklab/html/dockertidy_freeze /var/www/virtual/geeklab/docker-tidy.geekdocs.de',
        ],
        username: { from_secret: 'ssh_username' },
      },
    },
    {
      name: 'publish',
      image: 'appleboy/drone-scp',
      settings: {
        host: { from_secret: 'ssh_host' },
        key: { from_secret: 'ssh_key' },
        rm: true,
        source: 'docs/public/*',
        strip_components: 2,
        target: '/var/www/virtual/geeklab/html/docker-tidy.geekdocs.de/',
        username: { from_secret: 'ssh_username' },
      },
    },
    {
      name: 'cleanup',
      image: 'appleboy/drone-ssh:1.5.5',
      settings: {
        host: { from_secret: 'ssh_host' },
        key: { from_secret: 'ssh_key' },
        script: [
          'ln -sfn /var/www/virtual/geeklab/html/docker-tidy.geekdocs.de /var/www/virtual/geeklab/docker-tidy.geekdocs.de',
          'rm -rf /var/www/virtual/geeklab/html/dockertidy_freeze/',
        ],
        username: { from_secret: 'ssh_username' },
      },
    },
  ],
  depends_on: [
    'build-package',
    'build-container-amd64',
    'build-container-arm64',
    'build-container-arm',
  ],
  trigger: {
    ref: ['refs/heads/master', 'refs/tags/**'],
  },
};

local PipelineNotifications = {
  kind: 'pipeline',
  name: 'notifications',
  platform: {
    os: 'linux',
    arch: 'amd64',
  },
  steps: [
    {
      image: 'plugins/manifest',
      name: 'manifest',
      settings: {
        ignore_missing: true,
        auto_tag: true,
        username: { from_secret: 'docker_username' },
        password: { from_secret: 'docker_password' },
        spec: 'manifest.tmpl',
      },
    },
    {
      name: 'readme',
      image: 'sheogorath/readme-to-dockerhub',
      environment: {
        DOCKERHUB_USERNAME: { from_secret: 'docker_username' },
        DOCKERHUB_PASSWORD: { from_secret: 'docker_password' },
        DOCKERHUB_REPO_PREFIX: 'xoxys',
        DOCKERHUB_REPO_NAME: '${DRONE_REPO_NAME}',
        README_PATH: 'README.md',
        SHORT_DESCRIPTION: 'docker-tidy - Keep docker hosts tidy',
      },
    },
    {
      name: 'matrix',
      image: 'plugins/matrix',
      settings: {
        homeserver: { from_secret: 'matrix_homeserver' },
        roomid: { from_secret: 'matrix_roomid' },
        template: 'Status: **{{ build.status }}**<br/> Build: [{{ repo.Owner }}/{{ repo.Name }}]({{ build.link }}) ({{ build.branch }}) by {{ build.author }}<br/> Message: {{ build.message }}',
        username: { from_secret: 'matrix_username' },
        password: { from_secret: 'matrix_password' },
      },
      when: {
        status: ['success', 'failure'],
      },
    },
  ],
  depends_on: [
    'docs',
  ],
  trigger: {
    ref: ['refs/heads/master', 'refs/tags/**'],
    status: ['success', 'failure'],
  },
};

[
  PipelineLint,
  PipelineDeps,
  PipelineTest,
  PipelineVerify,
  PipelineSecurity,
  PipelineBuildPackage,
  PipelineBuildContainer(arch='amd64'),
  PipelineBuildContainer(arch='arm64'),
  PipelineBuildContainer(arch='arm'),
  PipelineDocs,
  PipelineNotifications,
]
