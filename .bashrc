export GIT_SSH=plink

export PROMPT_COMMAND='if [ "$(id -u)" -ne 0 ]; then echo "$(date "+%Y-%m-%d.%H:%M:%S") $(pwd) $(history 1)" >> ~/.bash.log; fi'

function hh() {
    grep "$1" ~/.bash.log
}

export TERM=cygwin

alias vim="TERM=xterm vim"
alias vi=vim
alias python="winpty -Xallow-non-tty python"

export VIDA_PIP_URL=https://artifacts.vidaprivacy.io/repository/vida-pi
export VIDA_PIP_USER=vida

# added by travis gem
[ -f C:/Users/erik/.travis/travis.sh ] && source C:/Users/erik/.travis/travis.sh
