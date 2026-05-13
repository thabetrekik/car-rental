pipeline {
    agent any

    environment {
        SONAR_HOST_URL = 'http://sonarqube:9000'
    }

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
                sh 'docker compose run --rm web python manage.py test'
            }
        }

        stage('SonarQube Scan') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh '''
                    docker run --rm \
                    --network car_rental_default \
                    -v $(pwd):/usr/src \
                    sonarsource/sonar-scanner-cli:latest \
                    -Dsonar.projectKey=car-rental \
                    -Dsonar.sources=/usr/src \
                    -Dsonar.host.url=http://sonarqube:9000 \
                    -Dsonar.login=squ_2da11ef8e1ce8ba43deb7d24492cd9a007e5f0be
                    '''
                }
            }
        }

        stage('Deploy Application') {
            steps {
                sh 'docker compose up -d'
            }
        }
    }

    post {
        always {
            echo 'Pipeline finished'
        }
    }
}