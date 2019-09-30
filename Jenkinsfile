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
          sh 'MYPYPATH="" flake8 --format=pylint .'
        }
      }
    }
    stage('Check Migrations are up to date') {
      steps {
        configFileProvider([configFile(fileId: 'multipoll-config', variable: 'MPOLLS_CONFIG_FILE')]) {
          withEnv(readFile(MPOLLS_CONFIG_FILE).tokenize("\n")) {
            withPythonEnv('System-CPython3.7') {
              sh 'python manage.py makemigrations --check'
            }
          }
        }
      }
    }
    stage('SLOC Count') {
      steps {
        sh 'sloccount --details multipoll > sloccount.sc'
        sloccountPublish encoding: '', pattern: ''
      }
    }
    stage('Record Issues') {
      steps {
        recordIssues aggregatingResults: true, enabledForFailure: true, tools: [flake8()]
      }
    }
  }
}
