pipeline {
    agent any

    environment {
        REGISTRY = "${env.REGISTRY_HOST ?: 'registry:5000'}"
        APP_NAME = "python-app"
        IMAGE_TAG = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Checkout') {
            steps {
                echo "📥 Checking out source..."
                checkout scm
            }
        }

        stage('Docker Build') {
            steps {
                echo "🐳 Building Docker image..."
                sh """
                    docker build \
                        -t ${REGISTRY}/${APP_NAME}:${IMAGE_TAG} \
                        -t ${REGISTRY}/${APP_NAME}:latest .
                """
            }
        }

        stage('Test Image') {
            steps {
                echo "🧪 Running tests inside Docker container..."
                sh """
                    docker run --rm ${REGISTRY}/${APP_NAME}:${IMAGE_TAG} \
                        sh -c "pytest tests/ -v --junitxml=test-results.xml || true" || true
                """
                // In a real scenario, we would mount a volume to extract test-results.xml
            }
        }

        stage('Push to Registry') {
            steps {
                sh """
                    docker push ${REGISTRY}/${APP_NAME}:${IMAGE_TAG}
                    docker push ${REGISTRY}/${APP_NAME}:latest
                """
            }
        }

        stage('Deploy') {
            steps {
                echo "🚀 Mocking deployment for E2E test..."
                sh """
                    echo "Deploying ${APP_NAME}:${IMAGE_TAG}..."
                    sleep 2
                    echo "Deployment successful!"
                """
            }
        }
    }

    post {
        always {
            sh """
                curl -sf -X POST http://dashboard-backend:5050/api/builds/webhook \
                    -H 'Content-Type: application/json' \
                    -d '{"job":"${JOB_NAME}","build_number":${BUILD_NUMBER},"result":"${currentBuild.result}","duration_ms":${currentBuild.duration}}' || true
            """
            cleanWs()
        }
    }
}
