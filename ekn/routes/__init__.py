import ekn.routes.misc as misc
import ekn.routes.registration as registration
import ekn.routes.users as users
import ekn.routes.voting as voting

categories = voting.categories
change_security = users.change_security
gdpr_view = users.gdpr_view
get_score = voting.get_score
get_current_key = users.get_current_key
get_vote_count = voting.get_vote_count
register_connection = registration.register_connection
register_service = registration.register_service
register_user = registration.register_user
verify_credentials_route = users.verify_credentials_route
version = misc.version
vote = voting.vote
