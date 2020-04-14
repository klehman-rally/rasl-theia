# rasl-theia
Rally-Slack integration theia simple Rally info retriever

## seerally
The initial swag at this is to supply a Slack slash command (/seerally)
that will take a parameter designating a Rally artifact via FormattedID
and return some summary information about that if it exists and can be found.

Some assumptions are baked in to this exploratory implementation.
   1) There's only 1 valid Slack team_id that can use the /seerally command
   2) There's only 1 valid Slack channel that can use the /seerally command
   3) Only 1 Rally Workspace will be searched for a FormattedID match
       "AC WSAPI Toolkit Python" with ObjectID of 101557541536

