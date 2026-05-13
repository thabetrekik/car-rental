pipeline {
    agent any

    environment {
        GITHUB_REPO = "https://github.com/thabetrekik/car-rental.git"
        SONARQUBE_SERVER = "SonarQube"   // Jenkins SonarQube server name
        SONARQUBE_PROJECT_KEY = "car-rental"
    }

    stages {

        stage('Checkout') {
            steps {
                git url: "https://github.com/thabetrekik/car-rental.git", credentialsId: 'github-token', branch: 'main'
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

        stage('Apply Migrations') {
            steps {
                sh 'docker compose run --rm web python manage.py migrate'
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${SONARQUBE_SERVER}") {
                    sh '''
                        docker compose run --rm web \
                        sonar-scanner \
                        -Dsonar.projectKey=Car-Rental \
                        -Dsonar.sources=. \
                        -Dsonar.host.url=http://sonarqube:9000 \
                        -Dsonar.login=squ_7e27e2fae5ba66c1b611df923199a156e4ea290d
                    '''
                }
            }
        }

        stage('OWASP ZAP Scan') {
            steps {
                sh '''
                    docker run --rm -v $(pwd):/zap/wrk \
                    owasp/zap2docker-stable zap-baseline.py \
                    -t http://web:8000 -r zap_report.html
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh 'docker compose run --rm web python manage.py test'
            }
        }

        stage('Deploy') {
            steps {
                sh 'docker compose up -d web nginx'
            }
        }
    }

    post {
        always {
            echo 'Pipeline finished'
            archiveArtifacts artifacts: 'zap_report.html', fingerprint: true
        }
        success {
            echo '✅ Deployment successful!'
        }
        failure {
            echo '❌ Pipeline failed. Check logs.'
        }
    }
}
