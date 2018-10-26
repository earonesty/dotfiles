export GIT_SSH=plink

export PROMPT_COMMAND='if [ "$(id -u)" -ne 0 ]; then echo "$(date "+%Y-%m-%d.%H:%M:%S") $(pwd) $(history 1)" >> ~/.bash.log; fi'

function hh() {
    grep "$1" ~/.bash.log
}`
