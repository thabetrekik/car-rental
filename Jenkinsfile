pipeline {
    agent any

    environment {
        GITHUB_REPO = "https://github.com/thabetrekik/car-rental.git"
        SONARQUBE_SERVER = "SonarQube"
        SONARQUBE_PROJECT_KEY = "Car-Rental"
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

        stage('Run Tests') {
            steps {
                sh 'docker compose run --rm web python manage.py test'
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv("${SONARQUBE_SERVER}") {
                    withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                        sh '''
                            sonar-scanner \
                              -Dsonar.projectKey=$SONARQUBE_PROJECT_KEY \
                              -Dsonar.sources=. \
                              -Dsonar.host.url=http://sonarqube:9000 \
                              -Dsonar.login=$SONAR_TOKEN
                        '''
                    }
                }
            }
        }

        stage("Quality Gate") {
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        // Start ALL services for ZAP (nginx + web)
        stage('Start Services for ZAP') {
            when {
                branch 'main'
            }
            steps {
                sh 'docker compose up -d web nginx'
                sh '''
                    echo "Waiting for nginx to be ready..."
                    for i in $(seq 1 30); do
                        docker run --rm --network car_rental_network curlimages/curl:8.5.0 -s -o /dev/null -w "%{http_code}" http://nginx:80 | grep -qE "200|302|401|403" && break
                        echo "Attempt $i: nginx not ready yet..."
                        sleep 2
                    done
                    echo "Nginx is ready!"
                '''
            }
        }

        stage('OWASP ZAP Scan') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    # Create temp dir with proper permissions
                    ZAP_TMP=$(mktemp -d)
                    chmod 777 $ZAP_TMP
                    
                    echo "Running ZAP scan against http://nginx:80..."
                    
                    docker run --rm \
                      --network car_rental_network \
                      -v $ZAP_TMP:/zap/wrk:rw \
                      zaproxy/zap-stable zap-baseline.py \
                      -t http://nginx:80 \
                      -r zap_report.html \
                      -I
                    
                    # Copy report to workspace
                    cp $ZAP_TMP/zap_report.html ${WORKSPACE}/zap_report.html || echo "No report generated"
                    rm -rf $ZAP_TMP
                '''
            }
        }

        stage('Deploy') {
            steps {
                sh 'docker compose up -d web nginx'
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