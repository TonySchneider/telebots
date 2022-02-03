node {
    timestamps {
        stage('Clean WS') {
            echo 'Cleaning work space'
        }
        stage('Pull updated code'){
            dir('/home/tony/telebots')
                sh """
                su tony
                git pull
                """
        }
    }
}