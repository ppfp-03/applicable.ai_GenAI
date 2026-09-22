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
  console.error('No virtual environment found. Follow the README setup to create .venv or venv and install requirements.txt.');
  process.exit(1);
}

const child = spawn(python, ['-m', 'streamlit', 'run', 'app.py', ...process.argv.slice(2)], {
  cwd: root,
  stdio: 'inherit',
});

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => child.kill(signal));
}

child.on('error', (error) => {
  console.error(`Unable to start Streamlit: ${error.message}`);
  process.exitCode = 1;
});

child.on('exit', (code, signal) => {
  process.exitCode = code ?? (signal === 'SIGINT' ? 130 : 1);
});
