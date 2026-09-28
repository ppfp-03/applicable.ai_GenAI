const { existsSync } = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const executable = process.platform === 'win32'
  ? ['Scripts', 'python.exe']
  : ['bin', 'python'];

const python = ['.venv', 'venv']
  .map((directory) => path.join(root, directory, ...executable))
  .find((candidate) => existsSync(candidate));

if (!python) {
  console.error(
    'No virtual environment found. Create .venv or venv and install requirements.txt.'
  );
  process.exit(1);
}

const env = {
  ...process.env,
  PYTHONPATH: path.join(root, 'src'),
};

const child = spawn(python, ['-m', 'pytest', ...process.argv.slice(2)], {
  cwd: root,
  stdio: 'inherit',
  env,
});

child.on('error', (error) => {
  console.error(`Unable to run tests: ${error.message}`);
  process.exitCode = 1;
});

child.on('exit', (code) => {
  process.exitCode = code ?? 1;
});
