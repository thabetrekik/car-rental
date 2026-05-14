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
                git url: "${GITHUB_REPO}", credentialsId: 'github-token', branch: 'main'
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
                sh 'docker compose run --rm web python wait_for_db.py'
            }
        }

    stage('SonarQube Analysis') {
        steps {
            withSonarQubeEnv('SonarQube') {
                sh """
                docker run --rm \
                -v ${WORKSPACE}:/usr/src \
                sonarsource/sonar-scanner-cli:latest \
                -Dsonar.projectKey=car-rental \
                -Dsonar.sources=/usr/src \
                -Dsonar.host.url=http://sonarqube:9000 \
                -Dsonar.login=squ_3773c8416e0d828e5e43bcdb563f3c4ca01f3c69
                """
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
        stage("Quality Gate") {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                waitForQualityGate abortPipeline: true
                }
            }
        }
        stage('Cleanup') {
            steps {
                sh 'docker compose down || true'
            }
        }


    }


    post {
        always {
            echo 'Pipeline finished'
        }
        success {
            echo '✅ Deployment successful!'
        }
        failure {
            echo '❌ Pipeline failed. Check logs.'
        }
    }
}
