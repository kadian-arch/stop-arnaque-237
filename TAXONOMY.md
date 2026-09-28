# Taxonomy

Codes used in every file. Generated from `pipeline/taxonomy.py`.

## Scam types (`scam_types`)

| Code | Meaning |
|---|---|
| `wrong_number_reversal` | Money sent 'by mistake', victim asked to send it back |
| `deposit_withdrawal_trap` | Small deposit followed by a withdrawal request the victim approves |
| `fake_prize_promo` | Fake prize, promo, lottery, coupon or giveaway |
| `account_blocked` | 'Your account is blocked or suspended' |
| `fake_agent_support` | Fake operator/bank agent or customer care |
| `credential_request` | Asked for PIN, OTP, code, or to dial a code |
| `family_emergency` | Relative or friend 'in an emergency' |
| `hacked_account_money` | Hacked social media account asking contacts for money |
| `fake_job` | Fake job, recruitment or internship |
| `fake_scholarship_visa` | Fake scholarship, visa, DV lottery or travel abroad |
| `fake_concours_admission` | Fake concours, exam results, admission or leaked exams |
| `investment_ponzi_crypto` | Investment, 'double your money', Ponzi, crypto |
| `loan_scam` | Loan offer or loan app |
| `fake_seller_delivery` | Fake seller, online shopping, tickets or delivery |
| `official_impersonation` | Fake government, police, customs, tax or public body |
| `romance` | Romance or relationship scam |
| `sim_swap` | SIM swap / lost control of number |
| `fake_social_profile` | Fake social media profile or page of a public figure or brand |
| `fake_document` | Forged communique, memo or tender circulated online |
| `phishing_link` | Link or site that harvests personal data or logins |
| `advance_fee` | Upfront fee demanded for a service, file, auction or funding |
| `other` | Other |

## Channels (`channel / channels`)

`sms`, `whatsapp`, `phone_call`, `social_media`, `website_app`, `email`, `in_person`, `other`

## Requested actions (`caller_asked / requested_actions`)

`give_pin_code`, `dial_code`, `send_money`, `send_airtime`, `give_id_personal_info`, `install_app`, `open_link`, `pay_fee`, `nothing_yet`

## Outcomes (`outcome`)

`noticed`, `almost`, `lost_money`, `someone_else_lost`, `unknown`

## Payment rails (`payment_rails`)

`mtn_momo`, `orange_money`, `bank`, `cash`, `airtime`, `crypto`, `other`

## Sender types (`sender_type`)

`personal_number`, `alphanumeric_name`, `social_account`, `hidden`, `unknown`, `other`

## Regions (`region`)

`adamaoua`, `centre`, `east`, `far_north`, `littoral`, `north`, `north_west`, `west`, `south`, `south_west`, `outside_cameroon`, `undisclosed`

## What people did after (`actions_after`)

`blocked_number`, `nothing`, `recovered_money`, `reported_antic`, `reported_operator`, `reported_police`, `told_family`

## When it happened (`when`)

`this_week`, `this_month`, `last_6_months`, `earlier_2026`, `2025`, `before_2025`

## How a call ended (`call_end`)

`hung_up`, `complied`, `they_stopped`, `ongoing`

## Who the caller claimed to be (`caller_claimed`)

`operator_staff`, `bank_staff`, `government_security`, `relative_friend`, `employer_recruiter`, `wrong_number_sender`, `other`
