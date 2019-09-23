pipeline {
  agent any
  stages {
    stage('Print Information') {
      steps {
        withPythonEnv('System-CPython3.7') {
          sh 'python --version'
          sh 'pip --version'
          sh 'python -c "import sys; print(sys.path)"'
          sh 'pip list'
        }
      }
    }
    stage('Install Dependencies') {
      steps {
        withPythonEnv('System-CPython3.7') {
          sh 'pip install --upgrade pip'
          sh 'pip install --upgrade setuptools'
          sh 'pip install -r requirements.txt'
        }
      }
    }
    stage('Install Flake8 Dependencies') {
      steps {
        withPythonEnv('System-CPython3.7') {
          sh 'pip install -r requirements.flake8.txt'
        }
      }
    }
    stage('Print Installed Packages') {
      steps {
        withPythonEnv('System-CPython3.7') {
          sh 'pip list -o'
        }
      } 
    }
    stage('Run Flake8') {
      steps {
        withPythonEnv('System-CPython3.7') {
          sh 'flake8 .'
        }
      }
    }
    stage('Check Migrations are up to date') {
      steps {
        withPythonEnv('System-CPython3.7') {
          sh 'python migrate.py makemigrations --check'
        }
      }
    }
  }
}