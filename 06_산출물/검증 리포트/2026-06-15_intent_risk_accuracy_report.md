# intent/risk EvaluationService 정확도 리포트

- run_id: `EVAL_27_FULL_20260615`
- evaluated_at: `2026-06-15T08:51:59.363665+00:00`
- 평가 케이스 수: 147
- 결과 JSON: `C:\Users\TAEHEE\Documents\2026 LGDX\프로젝트\lgdx_DX\07_개발단계\06_AR 가전케어 AI\02_데이터연동\eval_sets\intent_risk_eval_results_20260615.json`

## 핵심 정확도

| Metric | Value |
|---|---:|
| intent_accuracy | 0.5782 |
| risk_accuracy | 0.483 |
| action_accuracy | 0.4286 |
| procedure_accuracy | 0.4626 |
| ar_allowed_accuracy | 0.5102 |
| clarification_accuracy | 0.5986 |
| high_risk_recall | 1.0 |
| no_match_precision | 0.0 |

## 분포

```json
{
  "expected_intent": {
    "expert_as": 28,
    "self_as": 56,
    "self_care": 63
  },
  "predicted_intent": {
    "expert_as": 39,
    "self_as": 81,
    "self_care": 25,
    "null": 2
  },
  "expected_risk": {
    "high": 28,
    "medium": 56,
    "low": 63
  },
  "predicted_risk": {
    "high": 71,
    "low": 61,
    "medium": 15
  },
  "expected_action": {
    "route_to_service": 28,
    "prepare_ar_guide_session": 74,
    "prepare_limited_ar_safe_check": 15,
    "ask_clarification": 28,
    "manual_or_service_guidance_only": 2
  },
  "predicted_action": {
    "route_to_service": 39,
    "ask_clarification": 79,
    "prepare_ar_guide_session": 21,
    "manual_or_service_guidance_only": 1,
    "official_evidence_required": 7
  }
}
```

## Error Type Counts

```json
{
  "correct": 40,
  "clarification_error": 58,
  "intent_mismatch": 23,
  "risk_mismatch": 13,
  "no_match_false_positive": 7,
  "procedure_mismatch": 6
}
```

## 실패 케이스 목록

### IR_VOC_0582F38A0A26 - clarification_error

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_ar_guide_session', 'procedure_type': 'no_cooling_self_check', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'no_cooling_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: Fans with AC are weird, like if you are on the top floor in your building or if the guy above you doesn't use AC, you'll just end up getting heat from the top in your room. Like if you want fan like cooling why not just set the AC damper towards you. Will save electricity too

### IR_VOC_05FFEA7F81B6 - clarification_error

- product_type: `air_conditioner`
- expected: `{'intent': 'expert_as', 'risk': 'high', 'action': 'route_to_service', 'procedure_type': 'high_risk_troubleshooting', 'ar_allowed': False, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'high', 'action': 'ask_clarification', 'procedure_type': 'no_cooling_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: Think twice before purchasing Panasonic there after sales services are pathetic in just 1 year my ac pcb got damaged they took 2 months to repair now again cooling problem .. also they r demanding money now ... go for other brands ..my money is totally stucked.. i purchased 1.5 ton

### IR_VOC_0866FA446045 - clarification_error

- product_type: `air_conditioner`
- expected: `{'intent': 'expert_as', 'risk': 'high', 'action': 'route_to_service', 'procedure_type': 'high_risk_troubleshooting', 'ar_allowed': False, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'high', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: It is not worth buying. You will spend more on repairing (gas leaks) & electricity. For a long-term (4-5 years) period, you should go for a new AC. Thumb rule: ACs become shit after 4-5 years of use (most of the time).

### IR_VOC_003A40B41B51 - intent_mismatch

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_limited_ar_safe_check', 'procedure_type': 'power_troubleshooting', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'noise_self_check', 'ar_allowed': True, 'followup_question': False}`
- message: Need Advice on how to tackle the hotel management Hi guys, posting this from my alt as this is a bit embarrassing. So I'm staying in a 3 star hotel in NCR and it is company provided accomodation. I've been staying here for about 10 days now. There's a kettle in the room and I bought milk thinking I would drink it before sleep as I recently joined gym. I set it up to heat and went to washroom to wash my face and in that short span the milk boils and gets out of the kettle and into the socket below. There's a loud sound and then the AC stops (everything else is working). I think the fuse got blown and the AC was connected to it, as it is just above where the kettle is placed. Now, I need advice on how what my next steps should be? Do I tell the hotel staff? I'll only be staying here till 24th March. Will they penalize me for this? I don't know how to reach out as this is my first time staying in a hotel and my first company as well. Please help. TLDR: Shorted hotel room fuse because of kettle and AC is not working now. Need advice on next steps.

### IR_VOC_00439585C436 - clarification_error

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'expert_as', 'risk': 'high', 'action': 'route_to_service', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': False}`
- message: Sundeep g mere pass Daikin window AC 4star 1 ton h 2022m liya tha but with in 1year gass leakage low cooling problem.😢 M bhugat raha hu please koi na na le

### IR_VOC_0048B99ED947 - risk_mismatch

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'noise_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'high', 'action': 'ask_clarification', 'procedure_type': 'noise_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: Maine bluestar split 1.5 ton 3 star purchase kiya hai uske compressor mein sound aa rahi hai speed up down hone ki kya yeh normal hai

### IR_VOC_0053B287E8BA - clarification_error

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_limited_ar_safe_check', 'procedure_type': 'power_troubleshooting', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'no_cooling_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: In my daikin I set 29 than it goes up to 25-26 than trip after that room temperature at 29 than cooling start and goes 25 why this not working on set temperature

### IR_VOC_00FD1F899D41 - risk_mismatch

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'no_cooling_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'no_cooling_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: Mandeep ji sorry to say Daikin 2023 FTKM model is very bad for cooling, there specifications are totally fake. we don't have any device to check we just believe and purchase. After installation we just put complain, and company person come and said its ok but it extremely slow cooling issues. pl advise, only making video not helping customer without practical test .

### IR_VOC_011095002E3D - risk_mismatch

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'no_cooling_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'no_cooling_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: I am also suffering after buying daikin ac from 1year, cooling problems.

### IR_VOC_01290BA7B6CD - clarification_error

- product_type: `air_conditioner`
- expected: `{'intent': 'expert_as', 'risk': 'high', 'action': 'route_to_service', 'procedure_type': 'high_risk_troubleshooting', 'ar_allowed': False, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'high', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: Anyone suggest me the split AC ? I have napolean 1.5T AC, always has gas leakage problems, have decided this year to not sheel on that fixing its problems. Planned to boy no one my budger is 45k-47k. Im considering post sales services and decent features

### IR_VOC_01A478ED5A9B - risk_mismatch

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'no_cooling_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'no_cooling_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: Why u left out Blue star Wpool and OG? Many remotes r without backlit feature, Any1.5 T AC if its cooling watts is more than 5280 it is truly a 1.5 T Ac or else it is less than that

### IR_VOC_01AD3FA1E221 - clarification_error

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'noise_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_ar_guide_session', 'procedure_type': 'noise_self_check', 'ar_allowed': True, 'followup_question': False}`
- message: Which AC has no fan noise ? I have to do recording

### IR_VOC_01C38584D4A8 - risk_mismatch

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'noise_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'noise_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: Sir Mera Dakin ac h 3star 2018 model service karane ke bad bi us me Fer Fer sound aane lagati he fter one month of service

### IR_VOC_0228337260FE - clarification_error

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_limited_ar_safe_check', 'procedure_type': 'power_troubleshooting', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'no_cooling_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: Based on my experience, I would recommend considering a Bluestar non-inverter AC in 2025, if still available. I've found that while inverter ACs may struggle to cool effectively after a few years, non-inverter models, despite inconsistent temperature regulation, provide significant cooling. Their simpler, refrigerator-like technology makes maintenance affordable. Although non-inverter ACs are often considered less energy-efficient, their intense cooling often leads to users switching them off during the night, potentially offsetting higher power consumption. My seven-year-old Daikin 1.5-ton inverter AC has been problematic, while an eight-year-old 1.0-ton Bluestar non-inverter unit performs very well. Even the Daikin service technician suggested purchasing a non-inverter model. Apparently, even affluent consumers are now seeking out these non-inverter units.

### IR_VOC_059D07F25236 - intent_mismatch

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_limited_ar_safe_check', 'procedure_type': 'power_troubleshooting', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'manual_or_service_guidance_only', 'procedure_type': 'remote_operation', 'ar_allowed': False, 'followup_question': False}`
- message: Bro listen if u want the best go with panasonic 5 star split ac u even get app support with it how many ton depends on your room size but if u wanna save Money get 5 star variant panasonic ac comes with better warranty , customer service is good , and the special coating that they use is quite effective , in comes with 0.1 mm dust filter most ac comes with 0.2 to 0.5 so panasonic ac will provide cleaner air which is appreciated specially in delhi and app support is really important imagine waking up at 12 or 1 to turn off ac it's a small inconvenient but it's really irritating when u can't fall back asleep with app support u can set timer and it will automatically turn off Edit :- ogeneral and Mitsubishi makes some of the best ac available in the market but they are on the expensive side if budget isn't your concern then go with this 2 otherwise stick to panasonic

### IR_VOC_068897485248 - risk_mismatch

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: AC MAI HOOKHA KA SMELL A RAHA HAI KYA KARE

### IR_VOC_0BE67ABB077A - clarification_error

- product_type: `air_conditioner`
- expected: `{'intent': 'expert_as', 'risk': 'high', 'action': 'route_to_service', 'procedure_type': 'high_risk_troubleshooting', 'ar_allowed': False, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'high', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: I kindly say every one who is going to get a thaught of buying panasonic ac after watching this video kindly cancel your idea of panasonic and go to lg or Daikin my ac started smell whithin a month and they cleaned coil with hot water and hydrogen peroxide nothing worked gradually it passed a month and replacement window was closed later they changed evapourator coil which was 40 days old and still problem continues when i complained these so called panasonic technician clowns ask me to run my ac at 26° and not at 28° because at 28 compressor it getting auto shut off generating smell and now they also started making decisions of cancellimg the tickets instead of solving the issue . Sir i request you to stop promoting panasonic ac's atleaste that way people can be saved.

### IR_VOC_0EB449FE035F - clarification_error

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_ar_guide_session', 'procedure_type': 'odor_self_check', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: Sir maine ifb ka new ac lagaya h 5 star 1.5 ton, new ac me bhi kichad jaisi smeel aa rhi h, foam wash, ditergent wash, bhi krwa li lekin whi smeel aabhi bhi aa rhi h. Koi bhi ganda nala, ya room me smell nhi h l, ac me hi aa rhi h, sab kuch krwa liya but pta nhi kyu aa rhi h, second room me daikin me bhi aati thi lekin ab daikin wali to khatam ho gyi

### IR_VOC_23A19C7AC9CA - clarification_error

- product_type: `air_conditioner`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_ar_guide_session', 'procedure_type': 'odor_self_check', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: I brought 1 Ton Daiken AC .Very Very Smell came from Indoor Unit Even Daiken service team not sovled this problem Pl guide

### IR_VOC_0021F04EB86A - risk_mismatch

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'noise_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: Hello viewers. Today I am going to share my view on LGWFT7519PR automatic Top Load Washing machine. It is one of the best washing machine that I have operated till now. I have purchased this washing machine around 10 years back and till date I have not faced any issues. The Engineer who came for the delivery and installation was great and I still remember he gave some of the tips for the maintenance. Now some of the Great features: > This Washing machine uses very less Electricity. > Less amount or only the required amount of water is used and hence there wont be any of the wastage. > No need to keep checking for the options as this is Fully automatic. > The fuzzy option which automatically sets the best washing mode calculating as per the load makes our work even easier. Just dump all the clothes that needs to be washed and cleaned and then Hit the Fuzzy key. All set the machine will work on its own. > Very less noise in comparison to the other machines. > This machine style and design is very simple but features are really amazing. It has got 8 other programs in addition like quick wash, gentle wash, Tub clean, strong wash which is for jeans or strong clothes. Personally I feel this product is very useful and if we look for the service centers we can find many of the authorized service centers. Only thing we need to do is to call at the customer care number and then raise the problem. LG has a good network and they are providing good support as well. I will rate this washing 4/5 in comparison to its features and also Lg's support. A definite recommended product for a Family.

### IR_VOC_00288288EA78 - no_match_false_positive

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'noise_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'medium', 'action': 'official_evidence_required', 'procedure_type': 'noise_self_check', 'ar_allowed': False, 'followup_question': False}`
- message: I am using LG Semi automatic washing machine last 3 years. My LG washing machine is Blue colour in 7.0 kg it’s have a plastic body and Roller Jat pulsator, Lint Collector, Collar Scrubber and its have three functions for washing Gentle, Normal and Strong and also have a Spin window for dryer clothes. I don’t have issue or any complaints with this machine. Its wash our cloths very safely and the clothes are cleaning well as well as the dryer is also good. Mostly washing machines have a noise but LG washing machine is doing normal noise not too much. It wash my daily clothes with normal function as well as if I have any other clothes like bed sheet, covers or heavy clothes I wash all type clothes in strong function. I am very happy with this washing machine. It gives us clean clothes with low electricity consumption and I suggest to everyone, if they wants to purchase a washing machine then go for it.

### IR_VOC_002950934A37 - no_match_false_positive

- product_type: `washing_machine`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'limescale_care', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'official_evidence_required', 'procedure_type': 'remote_operation', 'ar_allowed': False, 'followup_question': False}`
- message: w-m.buyer: Hi, I don brush cuffs and collars and the washing is clean. I don have kids, so not sure about heavily soiled or kids uniforms. But white clothes are still white and any small stains are washed away without brushing. But if it heavy mud sta ... ins then u have to brush. AND there is one intence wash option for heavily soiled clothes which i found was not good as it takes lot of time and water . I tried it on bedsheets. instead i use cotton option with 60 degrees water. and it cleans well. I also use prewash and use ala bleach and little quantity detergent with white clothes. these are all for cotton clothes. I don use synthetic clothes, and there is one option for such clothes too which i havent tried. Water consumption is normal as in other front loaders. and my electricity bill has not taken a high side ,from which i beleive it doesnt draw much power. And fyi, i was looking at IFB aqua model, which has inbuilt hard water softner.there was only one review stating it was good. I called the IFB people for info, but they had no stock even in their factory and none of the home appliances had it. the features were good for this model. but only problem is that service of IFB is really bad, and performace reviews is less.The model is IFB aqua energie. I was looking for 6kg .It took me three months to decide b/w ifb n LG. I was decided on IFB. My LG is 6.5kg as they din have 6 with these features. But as the saying goes, there is no machine in comaprison to hand wash :-). Read More

### IR_VOC_00641ACE0BCE - intent_mismatch

- product_type: `washing_machine`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- message: Folks at LG seem to be having a problem, in replacing a ''broken Spin tub lid'' since more than two months. I purchased a LG WP-9033 from a local electronics dealer in Bangalore, after exchanging it to my old workhorse of 8 years, Videocon V-NA-400T. I rue the decision to this day. At the time of selling the machine, I wasnt informed that the said product would be ''discontinued'' in three months. I am told now, when I have logged a complaint(M-52176) that the product has been discontinued, and is a challenge for the folks at LG to find a replacement for the broken component. This inspite of still being in the warranty period. As I have been using other LG products(TV, Refrigerator) from LG, I was biased into buying the same brand. I was in for a great shock. The lint filter broke in the first one hour of the machine being delivered at home. The so called service technician said I had to pay, since they were not responsible for the damage. After a high drama, he relented and replaced the broken lint, free of cost after two days. The same pathetic service is continuing with LG(Not sure if this is the case in other cities, but in Bangalore(Ph: 26627788 - Contact person Manohar/Sanjeev), dont ever try calling the above number. Not speaking for others, but I for one will never ever buy another LG product for my home, no matter how good the product is. BTW, I am planning in replacing my LG washing machine sometime this dussera/diwali season to maybe : samsung, Whirlpool etc. Are they any good!!

### IR_VOC_00797C44E398 - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_limited_ar_safe_check', 'procedure_type': 'power_troubleshooting', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'power_troubleshooting', 'ar_allowed': False, 'followup_question': True}`
- message: I use to Salute LG company just because of great features and awesome product they have available with a good quality of product.in electronic machine. I really believed in LG company because my mom have purchase LG Washing Machine WD-1275QDT and I really like features of this model and my mom also like the features and I has went to buy in this washing machine I saw many features which so fantastic by Cut down on wasteful energy consumption with our Standby Power Zero feature. Even without switching off your main switch, this feature ensures that no electricity is supplied to your machine once it is powered off. I saw in this washing machine I like the best part of this washing machine capacity is 7.5 and maximum spinning speed is 1200 with a 1888LED display. I really recommend this company.

### IR_VOC_008178B46C5F - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_limited_ar_safe_check', 'procedure_type': 'power_troubleshooting', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'high', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: I had bought Fully Automatic Top loading washing machine model T7567TEELH in 2017. I have having repeated problems with the machine. Within 4months the water pressure sensor has to be changed. Then Had changed the PCB in Aug 19 costing Rs 5145/-. Again in Oct 19 had to change the pressure sensor costing Rs 1840/-. Now again the machine is not working. So many problems in a machine which is not even 3 yrs old is a cause for concern!!!! Is there a problem with the quality of the product it self?? LG should have recalled the model and corrected the errors as gone by companies with repute and who accord importance to their Brand Image.......I am totally frustrated with the product.

### IR_VOC_00889A1EE57B - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_ar_guide_session', 'procedure_type': 'noise_self_check', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: Last weekend I booked a LG F1256NDP5 6KG Washing Machine from Videks, Adyar, Chennai Cost of Washing machine: Rs.28700 We already have an IFB Digital 7KG @my home town. We are happy with the machine. Its running fine for the past 3 years. Except for one service we had to do because of the drum rotation got stuck. We didn't know why. As it was in the warranty perioed it was fixed free of cost and only the transportation cost we had to bear. Because services cannot be done onsite for digital models(told by IFB customer service). After a long wait and lots of reading on reviews, I decided to stick to the new technology in the market. Yes its only the Inverter Direct Drive that attracted me to buy LG. I booked it on Sat and I got it delivered on Sunday. LG representative came on Monday for installation. He prepared and setup the machine for use. Couple of accessories he brought. : ) Stand with wheels and Washing Machine cover - Rs. 1500 (No bills) didnt want to dissappoint him so paid it of. So in 30Min time he set it up for use and explained the basis and how to use it. I tried it out right away with all my piled up cloths. I used the cotton 60 1200 w/o prewash. It took 2:30 Min for the complete wash cycle. Once you switch on the machine it give a nice tune during startup. Even beep's when changing options. Once the wash cycle is complete it gives an end tune as well. I really liked it. : ) Intrestingly this machine doesnt flash out the time immediatly when we select the options. After setting up all the options and press the start button It rotates for 15sec in both directions and flashes the max. time for the wash cycle. I suppose it detects the load on the machine. I was impressed on this. I felt the depth of the drum is really small and that makes it very compact. Doesnt take much space just 2.5 feet by 2 feet. So the depth of the drum should just be around 18inches or less than that. After pressing start, keenly observed it for a while. It started taking the water in. Even when taking the water in it doesnt do it in one shot. It takes in some water and rotates in one direction and takes some more and rotates in the other direction. Once enough water is taken inand heated up the wash cycle continued for 1 hour and 30min. During all this it was really silent and there was hardly any vibration or jerk as I observed. I could feel very mild vibration only when I touch it, as on a cd player : ) a little more than that. But when it was doing the spin action @1200 there was quite some vibration. The overall wash quality was impressive. I could see even the dirt on the shirt collars were removed. And this could be achieved on any front loading one and the trick is when loading cloths you have to load it as a 'U' stack. Dont just roll it and throw it in. Stack all the cloths by straighting them and load it along the drum in a 'U' shape. this way I was able to load efficiently and this helps the wash efficiency as well. This was suggested to me by the LG representative. Collectively this machine scores good. I would give a score of 8/10. Even I saw the electricity usage very very less. This had an A+ rating because of the Inverter direct drive, I suppose. It has just been a couple of weeks of use. I hope it does well for a long time :) My weekends are more pleasent nowadays !

### IR_VOC_0008CDA21183 - risk_mismatch

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'noise_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'noise_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: I have bought this LG washing machine about 3 month ago and it delivers good service. And the customer care service is also good, they just install it in 2 days after my purchase. Because of fully automation it saved my lots of time .I just put cloths and detergent in it and rest is done automatically by this machine, even it dry my cloths at that point, if I iron my cloths, I can wear it .It clean my cloths very well . Because of fully automation the size of machine is slick design, not so big as semi automatic, a one drum of 6.2 kg done all the work in it, and less vibration in full swing . great product by LG.

### IR_VOC_000E873A722E - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_limited_ar_safe_check', 'procedure_type': 'power_troubleshooting', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': None, 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': None, 'ar_allowed': False, 'followup_question': True}`
- message: I bought the lg direct drive washing machine model f8068ldp a 3 years back and within the first year it showed problems with the door.and now its play button is not working. We called the service center and they sent an'idiot' who said the parts should be bought from Noida! I'm in Kerala and this is the 2nd week we are waiting for the repair with no washing being done! Pathetic lg pathetic people. Do not be fooled by the 10 year warranty on the machine.it does not include anything but the motor for the warranty.

### IR_VOC_001814DCF55E - intent_mismatch

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_ar_guide_session', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'tub_clean', 'ar_allowed': True, 'followup_question': False}`
- message: Hello friends today I m going to share my experience of LG washing machine. My mother was suffering from some physical problem. She was unable to work hard. But she has to wash his clothes beacuse of our daily needs she has to wash her clothes by hand. This was very painful for her. Mostly I used to wash her clothes when she was unable to sit properly on the floor. Home maid is not available in my colony. But when I was busy in doing something she used to wash and this caused her became more ill. Sometimes after coming back from his office my father had to wash his clothes. This was very hurting and painful for me. I was very concerned about My mother's health and I thought we must need a washing machine for our entire family. So we decided to bought LG washing machine. we all were very happy that our all problems has shorted out. One day I reached home and I was astonished to see my mom washing clothes by hands. Inspite of having washing machine in our home I asked her the reason for washing clothes by hands. then she replied that "Machine is still working but never worked good for heavy dirty clothes. it never clean clothing spot stain. It is also useless for cleaning collar and cuff of shirts. This machine does not clean white clothes. so I rub by hands it's collar and spot that's why I wash clothes by hands otherwise u can not wear this clothes. After wash I drain in machine. it's drain part is olso not very good. washing part requires a large quantity of water. it is only ok for drain in rainy season." After this incident I realised that our problem is still remain. And then I changed this useless washing machine.

### IR_VOC_00193262149E - intent_mismatch

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_limited_ar_safe_check', 'procedure_type': 'power_troubleshooting', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'tub_clean', 'ar_allowed': True, 'followup_question': False}`
- message: Automatic washing + drying with a single press of button is your single most important criteria, then this machine is for you. I loadit, set the program, select drying option and leave for office - I get clean and hygienically dried clothes by the time I am back at home! Machine operation is relatively quiet although after a few days it has got much louder. LG is the only company having a washing machine with built-in dryer in the market in India, so it is a monopoly as of date (2007). My major gripe is LG’s aggressive and unethical marketing strategies by which consumers can get possibly cheated - the store catalog for LG TROMM washing machines loudly advertises 7 year warranty (no conditions listed) - but after actually buying the machine I found that it has only 2 years warranty - I was told by the installation person that the rest 5 years has to be purchased separately as AMC at an additional cost of Rs 4.5K! This seems plain cheating and taking consumer for granted. It is time they were taken to consumer court and buyers made beware of their tactics! The drying time is too much, takes a minimum of 3 hours of time even for the lightest loads to get 100% drying. There is no indication on the front panel of which cycle is in progress - you need to guess from the remaining time display. The controls and indications are practically dumb.Drying is not 100%, if the full load of 3kg is used, practical drying capacity is limited to just 2kg! Anything more and I get wet clothes out of it! Its is supposed to remember where it left off when there is a power failure and resume from that point. It does this for washing, but I have not seen it do this for drying cycle. If power cuts off during drying it does not resume at all, so clothes remain wet. Their after sales service is virtually non-existent and they look for every excuse to avoid it, in my brief experience. I booked a complaint for the imperfect drying at 3kg load. I was called up by their service mechanic the next day to fix an appointment and was doing so when the call got disconnected. 3 days later when I called up the service dept I got to know that the complaint was simply "cancelled" due to "no-response"! I re-registered a complaint - this time when he called I fixed an appointment, but he never turned up. It's more than a month now since my first complaint and I am yet to see the service mechanic's face or receive any other call from them. ZERO customer service.

### IR_VOC_00071E3CD49C - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_limited_ar_safe_check', 'procedure_type': 'power_troubleshooting', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: We replaced our old washing machine with this beast.This is a 7.2 Kg Semi Automatic Washing Machine with so many odd features to get our head wrapped around but the it gets the job done. The Wash Motor is of 360 W which is very powerful with 15 min wash timer with 25 min soak timer that rotates in couple of minutes. Spin Motor is 260 W. But the real magic is inside the wash tub.They made this new blue coloured lint collector that is so effective even dust and mud gets caught up in that mesh. Around the wash tub while washing clothes, water forces out of hundreds of nozzles into the clothes.Even below there are some rollers that act as a cloth cleaner and they all work really really well. There is one trade off though, This many features also requires a lot of water.It takes nearly 8-12 litres of water below wash tub. But still pretty decent buy.

### IR_VOC_002A9C164E1D - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: LG products are really very good so, no need of introduction about it.We purchased it 2 years back and price is nearly 18, 000/-. It cleans the clothes perfectly and gives maximum satisfaction to the user.It mainly reduces our work.The usage is also very simple. Just fill the water in that drum and add detergent then pour your cloths in it.It will take hardly half an hour for washing.Then you have to add water 4 to 5 times for cleaning. It has the lint filters at corner so after completing the wash you can remove it and clean it.These lint filters are used as the brush for clothes. The automatic dryer is also available.Every thing in this machine is automatic so don't worry about anything.Its really worth for your money.Gives best wash.It looks very nice and occupy less place only. But the thing is that if, you have any problem then the spare are not easily available in local areas so, you have to directly contact with main branch only.we had face these problem. But gives best wash and easy usage.

### IR_VOC_00358ED5E067 - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_limited_ar_safe_check', 'procedure_type': 'power_troubleshooting', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: Hello friends, I wish to tell you my experience about washing machine I purchased this washing machine 8 months back in the amount of 16, 000 only. It was very exciting and free delivery. That is 6.2 kg and fully automatic and colour is blue and white . It is energy conservation and good saving. And in that machine feature presents are punch+3 plustor and turbo drum+ smart motions. Also durable at the core the stainless tub in this washing machine is best durable than plastic, and repels stains and odors. Also extensive in built jet spary plus with powerfull water spary washes off dirt and required detergent provides you that good wash performance without the use of hands beautiful forever. And design also very super. I am very happy with this washing machine. I recommended to buy this washing machine.

### IR_VOC_0043A5F8CEE3 - risk_mismatch

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: Hello All, We purchased a brand-new LG washing machine fully automatic on June 3rd 2023 and this is the worst mistake we ever did. This machine was purchased from Reliance Digital. We initially were looking for other brands like Bosch and other. The executive convinced us to go with this product. Our old machine was also LG which served good for our need and expecting the same we purchased this new machine and this turned out to be nightmare to us. • From the day one we noticed the machine is damaging our clothes like cloth tearing and over rubbing compared to our old Machine. • We raised a complain about the same and the customer service received is the worst. • We had to follow up multiple times to know the status and most of time calls were left unanswered • We even shared multiple videos and images explaining our issue, still they could not find a solution for the issue. • We strongly feel there a design fault on this machine and the company is not ready to address the issue and research on the same. • Water gets clogged on the detergent filler tray and they say it is as per design and nothing can be done over the course of time if we don’t remove the water that can lead to foul smell. • The service center team wants to pickup the machine and check for the issue, we let them take the machine and with the kind of experience we are going through with the company. We asked the company people to use the original packing material before taking the machine and they refused and picked the machine with no protective cover or any kind of materials while shifting. • This is not what is expected from a brand like LG and they had the machine in their service center for a week and returned back to us like a 5 yrs old machine with dents all around the machine which is adding to wound. • Even after one week at the service center the machine is returned as it is with no changes We are forced to use our old machine even after purchasing a new one, please do not trust the brand as we did and get into a mess like this. LG does not care about customer feedback.

### IR_VOC_0050F48512B0 - no_match_false_positive

- product_type: `washing_machine`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'official_evidence_required', 'procedure_type': 'remote_operation', 'ar_allowed': False, 'followup_question': False}`
- message: I have purchased a LG semiautomatic washing machine model number is P7552N3FA from SMART FURNITURE AND ELECTRONICS TIPTUR on 11/02/2019. I have noticed that lint filter was missing in the machine so I have contacted the dealer. Dealer behaved rudely and he said he was not responsible for any kind of complaints. I have contacted the LG customer support and registered a complaint.Next day LG technician visited our home but he don't know weather the machine comes with lint filter bag or not. I am not happy with the service provided by LG.The LG service technician should be aware of their products and we have contacted LG customer support team to get help from them not to visit our site just simply for he name of service.

### IR_VOC_00585626C0B3 - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_ar_guide_session', 'procedure_type': 'odor_self_check', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: I have this washing machine last 2 years and tell no problem . In this machine my clothes wash very clean . There are 8 type of wash program.1 fuzzy 2. Wool .3. Quick wash 4.jeans 5. tub clean 6 . favorite 7. Silent 8. Smart cleaning . We can use these procedure according to our requirements . In this machine LED display is available . This machine has multiwater flow , turbo drum , waterfall circulation and smart filter . In this machine jet sprey function is also available During rinse jet sprey removes the detergent stains completely because of that washing quality is good . Interior body is made of stainless steel .Through delay program we can delay our washing process . tub clean function helps us to clean our tub 's odor and dirt of drum . In my opinion this machine is very good and. Save my time

### IR_VOC_005A94450323 - no_match_false_positive

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_limited_ar_safe_check', 'procedure_type': 'power_troubleshooting', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'official_evidence_required', 'procedure_type': 'remote_operation', 'ar_allowed': False, 'followup_question': False}`
- message: Hello guys! I am sharing my views on washing machine that is of LG brand. LG is very popular brand as we know. But this model of LG washing machine is not so good. My friend bought this washing machine about 6 month ago. And now it is not working well and completely damaged now. This is not a user friendly machine because it takes too longer time for cleaning of clothes and yet cloths are not clean completely. Some dust remains in the clothes. It takes more ditegent and after that does not clean. And when you want to wash the washing machine it can not clean easily. Handling is very easy but durability is not so longer. Because it can damage at any time. And also it take more power for work. In its drier there is rod in middel and when you spin it all cothes bind to that rod which creates a problem. Style and design is very attractive of it but this provide very bad services to customer so I do not want to purchase this product.

### IR_VOC_0067071837D9 - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: I am a Like of LG products, LG Washing Machine have no confusing menus, it is very simple to operate.Just put your clothes in and it will take care of the rest, I bought this washing machine last two years ago and working is very nice in initial LG T72CMG22P is one the best model form the company. This is Automatic Top loading machine that is easy to use. It makes washing more comfortable for you. it is very durable, it comes with 2 year warranty. The Turbo drum rotate in oppsite direction of the pulsator so that clothes don't stuck during washing. Its waterfall function works so well that improve rinsing effect during washing. it comes with smart antibacterial filter that makes washing more hygenic. Air dry system works well too. I installd it myself, I am a fan of lg brand & its suppot service is very good

### IR_VOC_00719B9BA3A6 - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: Helllllo Friends.! we purchase this washing machine back in 2013. it is working properly till now non measure problem at all. 1.>satisafieis me 2.>made up of stainless steel 3.>10 yr warranty on motor 4.>at genuine price only once it shows "OE" and "AE" errors then I called customr care they guide me online I repair it at home my self these errors usually come by dirt particle stopping water entry its filter must be cleaned.also got lots of other moods for washing clothes.

### IR_VOC_007B98154AFE - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: Its really comfortable and easy to use even not loaded its easy to handle No maintenance no worries. it cleans cloths nice and gently compact and attractive design Company provides great service and support. Some More. a) Top-loading washing machine; 6.5 kg capacity b) Smart filter keeps bacteria at bay c) Stainless steel inner tub d) Turbo drum technology ensures lesser tangling of clothes and thus ensuring freshness and also increased shelf life of the machine e) Waterfall circulation enhances rinsing, circulation of water Over all in this price range this is the great washer!

### IR_VOC_00840CD62781 - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: LG company is well known for their best washing machines, they put indian condition into consideration while making products. LG T72CMG22P is one the best model form the company. This is Automatic Top loading machine that is easy to use. It makes washing more comfortable for you. it is very durable, it comes with 2 year warranty. The Turbo drum rotate in oppsite direction of the pulsator so that clothes don't stuck during washing. Its waterfall function works so well that improve rinsing effect during washing. it comes with smart antibacterial filter that makes washing more hygenic. Air dry system works well too. its fuzzy logic enabled with Digital Display that gives it a nice look. Service and support from LG care is quite appreciable. Overall this is a GOOD product to BUY.

### IR_VOC_00A64E267B3A - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: I have purchased this product around 6 months back model is LG 6.2 kg Fully Automatic Top Load Washing Machine (T72CMG22P). Design and control panel is quite good. Cleaning is impressive. I used Whirlpool earlier, this one found one step ahead. Very powerful machine with advanced washing features like turbo drum made of stainless steel, smart filter and waterfall circulation. Just set the program properly, it will do the job nicely and make you happy. Only one issue, it is shaking bit more while spinning compare to other models. I am happy using this and will recommend to buy.

### IR_VOC_00B3EF003C35 - intent_mismatch

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_limited_ar_safe_check', 'procedure_type': 'power_troubleshooting', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'tub_clean', 'ar_allowed': True, 'followup_question': False}`
- message: Mechine work is not saticefied.current bill is heavy charges, power cutt is not safed .cloths are very durty clean in mechinework.babis cloth is neat clean & happy saticefaction.blanket wach is long time, & not clean in dust.ladees cloths is neat clean& wach.the mechine is every time problems repeat.totally ok

### IR_VOC_00C15234A548 - no_match_false_positive

- product_type: `washing_machine`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'official_evidence_required', 'procedure_type': 'remote_operation', 'ar_allowed': False, 'followup_question': False}`
- message: LG(T7248TDDLL) washing machine one of the promise model from the LG company.i got recommend of this model from my friend. I am using this model from since one year. The function is very simple, the function is given by two ways one is automated program another one is manually feed program. this machine includes with delay feature, child lock, smart filter, aqua reserve, tub cleaner, temperature selection, 3 pulsator, turbo drum, jet spray. moderate in cleaning, digital panel looks very nicely, compare to other products durability is good, very stylish and compact in size, service is good overall one of the promising brand from LG.

### IR_VOC_00D9374597FB - intent_mismatch

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_ar_guide_session', 'procedure_type': 'odor_self_check', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'tub_clean', 'ar_allowed': True, 'followup_question': False}`
- message: Front loader LG washer has worked very well over the several years we have owned it. No service calls have been made towards it and it survived two moves. Plus this mold concern I keep hearing about hasn't been a problem for me. I leave the door open and clean the seal around it often.

### IR_VOC_013C0DAA0326 - no_match_false_positive

- product_type: `washing_machine`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'manual_or_service_guidance_only', 'procedure_type': 'remote_operation', 'ar_allowed': False, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'official_evidence_required', 'procedure_type': 'remote_operation', 'ar_allowed': False, 'followup_question': False}`
- message: Time durability for washing is not efficient. Rinsing and Spinning will done just for process. Not removes actual dirt and stains. we must soak and Pre wash our clothes before getting them to this Washing Machine. it consumes more current, observe carefully. if you want to clean perfectly then wash them twice in automatic mode . time spoiling. color fade and damages are seen when it works in improper way . it collects much fur from the clothes. resulting in no long lasting clothes. turbine will struck with a normal ground water. because the hard water filters are not at all good.

### IR_VOC_01B8B3FCDDE2 - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: I recently purchased a washing machine from LG. It is a top loading washing machine with maximum load to 6.2 KGs. It is also pre-programmed machine. It has 14 presets for various control in washing cloths. It has additional features to clean clothes like waterfall circulation, smart filters, I-sensor, fuzzy logic control and dry air flow etc. It is also not that heavy to carry as it weighs 29Kgs. which is convenient as compared to older washing machines. It is a very good washing machine indeed.

### IR_VOC_01DC851C37E0 - risk_mismatch

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: *Intro: ****LG WF**-**T7519PR** 6.5 Kg, top load **washing machine** that cares for you and your clothes. Fuzzy logic a built in load sensor automatically detects the laundry load and a microprocessor optimizes **washing** conditions such as ideal water level and **washing** time. You can set the Wash Program at Fuzzy and it would sense the appropriate **washing** method required to give your clothes the perfect wash. Turbodrum the unique technology that knows how to take care of your clothes while giving you the perfect wash. The dual direction rotating drum reduces tangling of clothes which ensures your clothes stay as fresh as and new for much longer than ever before. The **machine** also is now less susceptible to wear and tear giving you a longer life. Turbodrum allows the movement of the drum in the opposite direction of the pulsator, for a doubly-efficient wash action. I-sensor is a 7 sensor technology which automatically determines the ideal wash environment giving you the optimum wash and 100 detergent free clothes. The Sensor automatically detects detergent quantity, water temperature and water hardness so as to make best **washing** a**lg**orithm for **washing** and rinsing, ultimately giving best **washing** effect. 3 Step **Washing** makes the best **washing** performance with low tangling and is done in three steps. It gives the advantage of hand wash with best use of detergent. Air Dry when the drum rotates the air dry system sucks in air, thereby throwing a blast of air on the clothes. Thus air dry system by removing moisture leaves clothes absolutely free from bad odor & bacteria and also facilitates faster drying of clothes. Smart Clean the purpose of this cycle is to optimize the detergent residue during **washing** and rinsing cycles. In order to implement this effect, the washer adds more rinsing times with the advanced i-Sensor. The clothes are residue and detergent free. The other features are 10 Water level selection, pulsator Punch 3, fuzzy logic control, Smart Cleaning, Tub Clean, Silent, Favorite.

### IR_VOC_01EBF520AC78 - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'tub_clean', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: Lg washing Machine is not so effective as I have experienced using it .Initially it worked fine But as usage period increased I found change that its not washing dirt properly .A customer buys a product hoping that it will help him in work.But here every thing they tell its automatic,i will not hasitate to say washing machine damages clothes and not so effective in removing hard stains.women think that we wash clothes in washing machine our work is done but I found clothese still smells after washing also with machines.Dont u think its true.

### IR_VOC_0221B8C8EB63 - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'limescale_care', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: Is it suitable for hard water

### IR_VOC_02240DD6E30B - clarification_error

- product_type: `washing_machine`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_limited_ar_safe_check', 'procedure_type': 'power_troubleshooting', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: Hi, friends I am going to tell you my experience about washing machine I was purchase LG washing machine in Rs.16000 only. Last 6 month back. It was very amazing and free delivery. That is 6.2 kg and fully automatic and colour is blue and white. It is energy saving and better saving. And in that machine feature available is punch + 3 plustor and turbo drum + smart motions. Also durable at the core the stainless tub in this machine is more durable than plastic, and repels stains and odors. Also the revolutionary in built jet spary plus with powerfull water spary washes off dirt and excess detergent giving you that best wash possible without the use of hands beautifull forever. And design also very good .I am very happy with washing machine.

### IR_VOC_07775FB876BD - clarification_error

- product_type: `air_purifier`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_ar_guide_session', 'procedure_type': 'no_cooling_self_check', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'high', 'action': 'ask_clarification', 'procedure_type': 'no_cooling_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: 95% percent of the electricity is consumed by the compressor for cooling the air only and NOT the fan in the indoor unit. In winters you can just use the FAN mode which negligibly consume elec. Very disappointed with TechWiser for not technically understanding the concept. Low effort work.

### IR_VOC_0A5EC043687F - intent_mismatch

- product_type: `air_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'manual_or_service_guidance_only', 'procedure_type': 'remote_operation', 'ar_allowed': False, 'followup_question': False}`
- predicted: `{'intent': 'expert_as', 'risk': 'high', 'action': 'route_to_service', 'procedure_type': 'high_risk_troubleshooting', 'ar_allowed': False, 'followup_question': False}`
- message: Hi Techwiser, I am Ravi Kaushik, founder at AIRTH. I would like to point out the gaps in your background research. I am an aerosol scientist from IITB and have expertise to talk on the subject. AIRTH has two versions: winter version and summer version Air Purifier = fan + filter AC = fan + filter + compressor When you use your AC in "fan mode" -> compressor doesn't work Hence your claim that it will ruin the AC compressor @2:47 is completely wrong! Also, with fan mode the electricity consumption is 40W (equivalent to a ceiling fan).

### IR_VOC_0B5787465785 - intent_mismatch

- product_type: `air_purifier`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_ar_guide_session', 'procedure_type': 'odor_self_check', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'expert_as', 'risk': 'high', 'action': 'route_to_service', 'procedure_type': 'high_risk_troubleshooting', 'ar_allowed': False, 'followup_question': False}`
- message: Hi, I’m in Santa Monica, Ca (neighboring city to Pacific palisades fire here in LA) does a carbon filter apply for those of us that outdoor air is not an option. I have sensitive lungs from mold illness and young kids. Would love some advice or recommendations for the purifiers I currently own. For context: I have hepa filters purifiers but will def consider the clean air kits after watching your video for the future.

### IR_VOC_1391043EB9E8 - intent_mismatch

- product_type: `air_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'limescale_care', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_replacement', 'ar_allowed': True, 'followup_question': False}`
- message: Cons bhi batao bhai, like no tds control and electricity dependency

### IR_VOC_040BC7C0B200 - clarification_error

- product_type: `air_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'limescale_care', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: Aquaguard uses MTDS (taste adjuster). MTDS (Mineral/Taste adjuster) works by Mixing a small amount of raw water back into RO water to increase TDS. which sounds like hack to me.

### IR_VOC_0C2120C426B6 - clarification_error

- product_type: `air_purifier`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_ar_guide_session', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: How it is working now? What about filter change and how often pre filter should be changed , it has so many bad reviews about low tds 20/30 ,,, and also leakage issue , service cost is too high,,, pls rply i want buy but confused,,, i want stainless steel storage take with 8 litres pls rply i wil be waiting

### IR_VOC_00662D5D11C3 - clarification_error

- product_type: `air_purifier`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_ar_guide_session', 'procedure_type': 'odor_self_check', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: What about using a MountainAir carbon filter is the best filter for growing cannabis completely gets rid of the smell

### IR_VOC_00AC314CE9E3 - procedure_mismatch

- product_type: `air_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_replacement', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- message: 1. H13 Hepa Filter 2. CADR: 100 cfm 3. Cost of filter replacement 4. How kften the filter should be changed? 5. How many separate parts are there in the filter? 6. Don't need ionizer in air purifier 7. Simple controls, don't need bluetooth, wifi in it

### IR_VOC_00E497FCC33E - procedure_mismatch

- product_type: `air_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_replacement', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- message: Truth is no filter is capable of filtering beyond 10-11 months without being changed

### IR_VOC_0132DB4AD933 - risk_mismatch

- product_type: `air_purifier`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: Will this also help with cooking odor?

### IR_VOC_01AD092561F1 - procedure_mismatch

- product_type: `air_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_replacement', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- message: What about Lasko electrostatic air purifier? It has permanent air filter and ozone filteration too. No need to change air filter.

### IR_VOC_01DD4EBACC9E - clarification_error

- product_type: `air_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: The problem with HEPA filters are once you clean them with water. It defeats the purpose.

### IR_VOC_0227C4582C91 - procedure_mismatch

- product_type: `air_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_replacement', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- message: Air purifier recommendations So I need a good air purifier. Filter should be easy to replace and if it is compact then it's much better. Any recommendations.

### IR_VOC_028AAD9C51A2 - no_match_false_positive

- product_type: `air_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'official_evidence_required', 'procedure_type': 'remote_operation', 'ar_allowed': False, 'followup_question': False}`
- message: 66min to clean a room is unreasonable. 20-30 min is the most you should consider. i commend vineet for testing this properly in the same room. other people don't even bother testing it with a proper AQI meter. pm2.5 should be under 30 as per US AQI standard. ignore regulations set by a parliamentary country. There are other air purifier's from honeywell that sell filters for reasonable prices. coway is out of stock for most of the year. same goes with other panasonic models and air filter availability is a challenge for many companies.

### IR_VOC_02AA43DD9290 - clarification_error

- product_type: `air_purifier`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_replacement', 'ar_allowed': True, 'followup_question': False}`
- message: sorry but this thing is BS and dangerous, in nature bugs eat mold off of moss so without anything keeping it in check this could become a biohazard

### IR_VOC_033428E1A52E - procedure_mismatch

- product_type: `air_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_replacement', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- message: 1:40/1:60 not only atumbarg ao Smith also same filter replacement one year comprehensive warranty

### IR_VOC_03FCE27DFD90 - procedure_mismatch

- product_type: `air_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_replacement', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_cleaning', 'ar_allowed': True, 'followup_question': False}`
- message: II think the replacement filters for those expensive air purifiers are also way more expensive.

### IR_VOC_040DC3F54E10 - risk_mismatch

- product_type: `air_purifier`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'low', 'action': 'ask_clarification', 'procedure_type': 'odor_self_check', 'ar_allowed': False, 'followup_question': True}`
- message: As someone who literally just wanted to address that slight smell of cat litter, regardless of cleaning them everyday. They work amazing, cheap small govee model. Super happy with it. Informative video, thank you!

### IR_VOC_13694F99564F - intent_mismatch

- product_type: `water_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'limescale_care', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'expert_as', 'risk': 'high', 'action': 'route_to_service', 'procedure_type': 'high_risk_troubleshooting', 'ar_allowed': False, 'followup_question': False}`
- message: @fit tuber mere ghar p borewell ka pani h or uska tds 240 k as pas h, to uske lie water purifier jrurt h kya, kyunki taste acha nhi h, ek gravity based water purifier ata h, bina electricity k chlta h , please uspe b ek video bnao, and please suggest better gravity based water purifier. Thanks in advance.

### IR_VOC_1F4DA7F6578C - intent_mismatch

- product_type: `water_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_replacement', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'expert_as', 'risk': 'high', 'action': 'route_to_service', 'procedure_type': 'high_risk_troubleshooting', 'ar_allowed': False, 'followup_question': False}`
- message: Factually wrong. After 2 years you are not extending warranty they just saying estimated filter cost is 5k (yes it is 5k now not 4.5k). Even they may take service charges, electric part replacement etc.

### IR_VOC_567ABFFAE4E9 - intent_mismatch

- product_type: `water_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'limescale_care', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'expert_as', 'risk': 'high', 'action': 'route_to_service', 'procedure_type': 'high_risk_troubleshooting', 'ar_allowed': False, 'followup_question': False}`
- message: Bro TDS level 720.iruku bro entha purifire vangalam sollunga bro

### IR_VOC_5E4EE210A353 - clarification_error

- product_type: `water_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_replacement', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'high', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: UrbanClap Native water purifier service is absolutely pathetic and highly misleading. The so-called 2-year warranty feels like nothing more than a marketing gimmick—it gives customers a false sense of security, but in reality, it offers almost no practical benefit. Reaching customer support itself is a frustrating experience, as you are forced to deal with a useless chatbot, and getting connected to a real person is extremely difficult. I own a Native M2 purifier, and it has been wasting an excessive amount of water. Despite clearly explaining the issue, the technician refused to take any meaningful action. He openly stated that filters and cartridges will not be replaced under any condition unless they are completely choked, even if the purifier’s performance is poor or water wastage is high. Shockingly, he didn’t even replace the pre-filter and claimed it is only changed after two years, regardless of usage or water quality, which makes absolutely no sense. This clearly shows that the service is driven by rigid policies rather than actual customer needs. You end up paying for a service plan where filters are not replaced when required, cartridges are practically never changed, and real issues like water wastage are completely ignored. The technicians simply hide behind policy excuses instead of providing solutions. Overall, this is not customer service—it’s pure negligence. Very disappointing experience and definitely not recommended.

### IR_VOC_5F6034D733E4 - intent_mismatch

- product_type: `water_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_replacement', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'expert_as', 'risk': 'high', 'action': 'route_to_service', 'procedure_type': 'high_risk_troubleshooting', 'ar_allowed': False, 'followup_question': False}`
- message: Electricity cost, waste water, filter change cost elam sertha athukku water can eh vaangitu poiralam. i've used water purifier for 6 years. enakke pirichu filter maatha theriyum. tds meterum vachuruken but athukke set aagala.

### IR_VOC_6164FEC84C47 - intent_mismatch

- product_type: `water_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'limescale_care', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'expert_as', 'risk': 'high', 'action': 'route_to_service', 'procedure_type': 'high_risk_troubleshooting', 'ar_allowed': False, 'followup_question': False}`
- message: my home tap tds is 175 and purifire 170

### IR_VOC_643A3E722CF8 - clarification_error

- product_type: `water_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'limescale_care', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'high', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: I find the author biased towards urban company because there are two important points here 1. Inorder to maintain tds in kent and atomberg the water only bypasses RO FILTER but still passes through all other filters so saying that unfiltered water is mixed with filtered water is entirely not true 2. In expense of atomberg the author has added cost of PCB also i.e. 1500 which is wrong and the actual cost is 3460 for filters and service as per image given by him

### IR_VOC_6BABEF15707E - clarification_error

- product_type: `water_purifier`
- expected: `{'intent': 'expert_as', 'risk': 'high', 'action': 'route_to_service', 'procedure_type': 'high_risk_troubleshooting', 'ar_allowed': False, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'high', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: It is very bad purifier in terms of service.The priti fire notified water nicely but it waste a lot of water and it is very difficult to use it.To operate it it is tough. The purifier is made up of good quality material but it id only for sometime and it is bad and weak ager sometime. It is very difficult to calendar it because it is too heavy in lifting it and carrying it. Style and design is pretty nice but they are of no use. The worst feature of this purifier is it's service which us very bad and service support from the company is also very bad.Please help us. Thank you.

### IR_VOC_75CCFF3C779B - clarification_error

- product_type: `water_purifier`
- expected: `{'intent': 'self_care', 'risk': 'low', 'action': 'prepare_ar_guide_session', 'procedure_type': 'filter_replacement', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'high', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: This is honestly next-level content. Setting up a full-fledged chemical lab and electrical lab just to test water purifiers isn’t something you see every day—especially in India. Most reviews stop at surface-level opinions, but this approach actually brings science, data, and accountability into the picture. The effort to analyze both the filtration process and the post-filtered water quality shows real intent to educate, not just influence. This is the kind of standard that can genuinely change how people evaluate products that directly impact health. Respect for raising the bar so high—this isn’t just a review, it’s a benchmark.

### IR_VOC_7D5B50747E29 - clarification_error

- product_type: `water_purifier`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'prepare_ar_guide_session', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': True, 'followup_question': False}`
- predicted: `{'intent': 'self_as', 'risk': 'high', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: Never ever buy any of lg's waterpurifier , Lg is worst in service of water purifier in India, I am frustrated for 2.5 years now because of the service. Spare parts are so expensive that you can buy another water purifier in it, I did a AMC of 1 year which costs 6500 , AMC covers all the filters , electrical components , and any leakages. After I purchased the AMC , after the first service there was a leakage in the filter which i complained to the technician. And now he says any complaints will be taken after 90 days of date of purchase of the AMC. This is clearly a fruad. If I am buying a 12 months they are straight away wasting 3 months of that. This is ridiculous as lg is such a huge brand in India

### IR_VOC_0546C0E785B6 - risk_mismatch

- product_type: `water_purifier`
- expected: `{'intent': 'self_as', 'risk': 'medium', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- predicted: `{'intent': 'self_as', 'risk': 'high', 'action': 'ask_clarification', 'procedure_type': 'water_leak_monsoon', 'ar_allowed': False, 'followup_question': True}`
- message: Shop se bhi Check kar ke lena chahiye. Maine lajpat rai market se 2700 me liya tha ghar jake install karaya to uska water tank leakage tha, Shopkeeper bolta hai tumne hi gira diya hoga pehle check karna tumhari jimmedari hai, fir Naya tank liya majburi me

- 실패 케이스가 107건이라 상위 80건만 표시했다. 전체는 결과 JSON을 확인한다.

## 비고

- Evaluation output is file-based because the final SQLite schema is frozen at 21 persisted tables.
- expected_intent means expected service_flow_type: self_care, self_as, or expert_as.
- no_match_precision treats official_match_review_needed/official_evidence_required as predicted no-match actions.
- LLM is not the final authority; rules, RAG evidence, and DecisionEngineV2 remain authoritative.

## 평가 후 결정

```json
{
  "rule_fix_applied_in_this_step": "High-risk keywords were extended with fire/flame/burnt/burn out, and high-risk decisions now force procedure_type=high_risk_troubleshooting.",
  "next_rule_corrections": [
    "Clarification gate is too aggressive for long VOC paragraphs that already contain enough symptom context.",
    "Remote/mode keyword matching still creates false remote_operation matches in washing machine and air purifier VOC text.",
    "Air purifier filter replacement and filter cleaning need clearer procedure priority.",
    "Official RAG coverage gaps for non-AC procedures cause official_evidence_required false positives."
  ],
  "llm_adapter_decision": "LLM adapter should be used as non-authoritative extraction assistance for mixed Hindi/English long VOC text, especially symptom summary, product family, and clarification necessity.",
  "training_classifier_decision": "Do not introduce a separate training-based classifier yet. The 147-case set is currently a golden evaluation set; rule/RAG/LLM-adapter corrections should be tried before fine-tuning or local classifier training."
}
```
