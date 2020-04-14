#!/bin/bash
#
# usage: deploy_func.sh <GCF_function_name> <entry_point_function>
#
#   needs these ENV vars set from the outside for use here:
#     GCP_PROJECT
#     GIT_BRANCH
#
colorize() { CODE=$1; shift; echo -e '\033[0;'$CODE'm'$*'\033[0m'; }
bold()   { echo -e $(colorize 1 "$@"); }
red()    { echo -e $(colorize 31 "$@"); }
green()  { echo -e $(colorize 32 "$@"); }
yellow() { echo -e $(colorize 33 "$@"); }
cyan()   { echo -e $(colorize 36 "$@"); }
reset()  { tput sgr0; }

FUNCTION_NAME=${1}
ENTRY_POINT=${2}
STD_REGION="us-central1"
REGION=${STD_REGION}
RUNTIME=python37

PROD_INDICATOR="-prod-"
if [[ "$GCP_PROJECT" =~ "$PROD_INDICATOR" ]]
then
    ENV_VARS_FILE=prod.env.yml
    TOPIC_PREFACE=""
else
    ENV_VARS_FILE=dev.env.yml
    TOPIC_PREFACE="dev_"
fi


#case $FUNCTION_NAME in
#
#  "oofrab_noodle")
#    TRIGGER_TOPIC="bangotron"
#    ;;
#
#  *)
#    TRIGGER_TOPIC=""
#    ;;
#esac

PUBLIC="--allow-unauthenticated"

yellow "Deploying $FUNCTION_NAME from $GIT_BRANCH branch to $GCP_PROJECT"

COMMAND="gcloud functions deploy ${FUNCTION_NAME} --entry-point ${ENTRY_POINT} \
                --env-vars-file env/${ENV_VARS_FILE} \
                --runtime ${RUNTIME} --region ${REGION}"

if [[ "${TRIGGER_TOPIC}" ]]
then
  COMMAND="$COMMAND --trigger-topic ${TOPIC_PREFACE}${TRIGGER_TOPIC}"
else
  COMMAND="$COMMAND --trigger-http ${PUBLIC}"
fi

cyan $COMMAND
eval $COMMAND
