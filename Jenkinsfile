pipeline {
  agent any
  stages {
    stage('Install Dependencies') {
      steps {
        withPythonEnv('System-CPython3.7') {
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
    stage('Run Flake8') {
      steps {
        withPythonEnv('System-CPython3.7') {
          sh 'flake8 .'
        }
      }
    }
  }
}