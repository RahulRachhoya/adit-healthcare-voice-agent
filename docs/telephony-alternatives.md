# Telephone trial alternatives

Research date: September 15, 2026. Budget remains zero out of pocket.

**Update: Vobiz is verified.** The owner created the account and supplied SIP
credentials. Its console displayed completed KYC, ₹25 trial credit and an active
trial caller ID. Vobiz and LiveKit outbound trunks were configured, and one real
India call completed with a saved booking, playable recording and automatic
Opik score of 1.0. It used ₹0.76 of trial credit; no payment was made. See
[actual call evidence](call-evidence.md).

The other rows below preserve earlier public research and signup checks. The
owner had confirmed access to either an Indian or US consenting test recipient.

The owner subsequently confirmed that **Sinch** signup displays a message to
contact its help line. This is a user-reported signup blocker; the exact error
was not independently inspected because browser access was unavailable.

## Candidates

| Provider/product | Published trial | Material limitation | Assessment fit |
|---|---|---|---|
| Vobiz | INR 25 credit and an active trial caller ID observed in this account | Eligibility, verification and trial number availability remain account-specific | Verified with one real LiveKit SIP call using trial credit, completed KYC and India routing |
| SIP.US | 60 minutes, no credit card or commitment; its current FreePBX FAQ includes the lower 48 US states and Canada | Its actual signup form says services are only available to businesses based in the United States and Canada | Excluded for the owner's India-based account, even with a US recipient |
| Sinch Elastic SIP Trunking | Test credits, a free test number and trial SIP trunks | Verified destinations only; five-minute calls; US, Canada, Puerto Rico and US Virgin Islands only | Signup blocked by the owner-reported help-line message. Credit amount, India-based account eligibility and real LiveKit interoperability remain unverified |
| Sinch Programmable Voice v2 | Self-created accounts receive test credits; documentation includes SIP and streaming channels and a test number for the first two weeks | Verified phone destinations only, one concurrent phone call, calls limited to a few minutes; no precise initial credit amount stated | Sinch signup is currently blocked. Even after signup, the account must confirm +91 eligibility and SIP access before implementation or any completion claim |
| Vonage Voice API | EUR 2 trial credit | Voice calls only to the number used at registration; trial credit cannot buy virtual numbers | Secondary candidate. Usable caller ID and a zero-payment LiveKit connection are not verified |

Sinch documents a Programmable Voice SIP endpoint with username/password
authentication. Without an application callback, it can route the SIP destination
to the telephone network. Caller ID must be a Sinch number or an account-verified
number. This suggests a potential fit with LiveKit's generic authenticated
outbound trunks; interoperability and trial permissions still require testing.
Do not apply Programmable Voice trial terms to Sinch's separate Elastic SIP
product.

## Excluded routes

- **SIP.US:** Selected `NO` for "Are you based in the United States / Canada?"
  on the official signup page. The form displayed "SIP.US services are only
  available to businesses based in the United States and Canada." No personal
  details were entered, terms accepted or signup submitted. Its KYC page also
  describes identity/business verification; this is not a no-verification option.
- **Telnyx:** LiveKit's own provider guide explicitly says a paid Telnyx account
  is required. Trial credit is therefore insufficient evidence of suitability
  for this zero-payment project.
- **Current Twilio trial:** Its console already requires funds for Elastic SIP
  Trunking. Current Voice trial documentation also blocks `Stream`,
  `ConversationRelay` and `Dial/Sip`, so a streaming connector does not resolve
  this account's restriction.
- **Current Plivo account:** The earlier observed India-number business-KYC
  requirement remains unresolved.

## Selection

**Use the existing verified Vobiz route.** Public documentation alone did not
establish that its trial caller ID would work with LiveKit. The subsequent
account check and actual answered call supplied that evidence. A number
purchase was not required for this test. This result does not guarantee
identical eligibility for a different account or destination.

Sinch remains blocked at signup. Its Elastic SIP trial guide, updated April 22,
2026, lists business details, credit
and KYC checks, and a sales contract under upgrading to production. Trial calls
use supplied credits and verified numbers. The guide also says EST customers
must be billed through a North American entity; whether that affects this
India-based trial signup remains unverified. Do not read the guide as a
guarantee of card-free or verification-free account activation.

The Sinch signup page accepts an email address at its first step and explicitly
says that clicking Continue agrees to its terms. The page has been opened for
the owner; no email or other personal information was entered and Continue was
not clicked.

Sinch Programmable Voice is a separate product, with signup and +91 trial
calling as unresolved prerequisites. It is not used by the verified application.

Before enabling the existing application, verify trial credit, an authorized
caller ID, recipient eligibility, compatible SIP authentication and the absence
of any required payment. Then make one explicitly authorized short call and
preserve its real evidence. Signup success alone does not complete this check.

## Official sources

- Vobiz trial credit and setup:
  `https://vobizai.mintlify.app/quick-start`
- Vobiz LiveKit integration and caller-ID requirement:
  `https://vobizai.mintlify.app/integrations/livekit`
- Vobiz trial-number restrictions:
  `https://vobizai.mintlify.app/faq/trial-inbound`
- Vobiz individual and company KYC:
  `https://vobizai.mintlify.app/compliance/india/kyc`
- SIP.US current trial FAQ:
  `https://www.sip.us/sip-for-freepbx/`
- SIP.US signup and KYC:
  `https://www.sip.us/get-started/`
  `https://www.sip.us/why-kyc/`
- Sinch Elastic SIP trial:
  `https://community.sinch.com/t5/Elastic-SIP-Trunking/How-do-I-get-started-with-an-Elastic-SIP-Trunking-trial/ta-p/18725`
- Sinch Programmable Voice accounts:
  `https://developers.sinch.com/docs/voice-2.0/accounts`
- Sinch signup:
  `https://dashboard.sinch.com/signup`
- Sinch Programmable Voice SIP connection:
  `https://developers.sinch.com/docs/voice-2.0/api-reference/phone/inbound`
- Vonage trial credit:
  `https://api.support.vonage.com/hc/en-us/articles/204014853-How-do-I-add-test-numbers-during-my-Vonage-API-trial`
- Vonage restrictions:
  `https://api.support.vonage.com/hc/en-us/articles/212554438-What-are-the-limitations-of-a-trial-account`
- LiveKit Telnyx requirement:
  `https://docs.livekit.io/telephony/start/providers/telnyx/`
- Twilio trial Voice restrictions:
  `https://www.twilio.com/docs/usage/trials/try-out-voice`
- LiveKit generic SIP configuration:
  `https://docs.livekit.io/telephony/start/sip-trunk-setup/`
