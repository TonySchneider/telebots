node {
    timestamps {
        stage('Clean WS') {
            echo 'Cleaning work space'
        }
        stage('Pull updated code'){
            dir('/home/jenkins/telebots'){
                sh """
                echo 'pulling code'
                git pull
                """
            }
        }
        stage('Deploy bot services'){
            dir('/home/jenkins/telebots'){
                 withCredentials([string(credentialsId: 'english_token_bot', variable: 'TOKEN'),
                                  usernamePassword(credentialsId: 'mysql_credentials', passwordVariable: 'password', usernameVariable: 'username')]) {
                    sh """
                    echo 'Sets necessary environment variables'
                    export TONY_ENGLISH_BOT_TOKEN='${SECRET}' && export MYSQL_USER='${username}' && export MYSQL_PASS='${password}'
                    echo 'Killing all screen sessions'
                    killall screen
                    echo 'attaching new screen session'
                    screen -d -m python3 telebots/tony_english_bot.py
                    """
                }
            }
        }
    }
}