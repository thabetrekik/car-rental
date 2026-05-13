pipeline {
    agent any

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Containers') {
            steps {
                sh 'docker compose build'
            }
        }

        stage('Start Database') {
            steps {
                sh 'docker compose up -d db'
            }
        }

        stage('Run Tests') {
            steps {
                sh 'docker compose run --rm -w /app web sh -c "ls -la /app && python manage.py test"'
            }
        }

        stage('Deploy') {
            steps {
                sh 'echo "Deploy step here"'
            }
        }
    }

    post {
        always {
            echo 'Pipeline finished'
        }
    }
}