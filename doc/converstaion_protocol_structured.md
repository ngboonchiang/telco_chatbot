Troubleshooting Protocol:


#0. Introduction & Issue Confirmation
##Data to Collect from the User:
Determine whether the user is experiencing a slow data issue and wishes to proceed with troubleshooting.

##Approaches for LLM to Collect the Required Data:
a. State the Purpose Clearly – Explain that the troubleshooting process is specifically designed to resolve slow data issues.
b. Confirm the User’s Issue – Directly ask the user if slow data is the problem they need help with.

##Conditions to Determine the Next Step:
*if the user confirms they are experiencing a slow data issue and wish to troubleshoot it-Step 1 Determine whether the issue happens everywhere or just in specific places
*if the user does not wish to solve the slow data issue-Step 51 Close the Chat
*if the user's response is unclear-remain



#1. Determine whether the issue happens everywhere or just in specific places
##Data to Collect from the User: 
Determine whether the issue happens everywhere or just in specific places

##Approaches for LLM to Collect the Required Data:
a. Ask the User About Location-Specific Issues – Directly ask the user whether they experience slow data only in certain areas or everywhere.
b. Provide Context and Examples to Help the User Answer – Give the user examples of location-based issues to ensure clarity.
c. Ask Follow-Up Questions if the Response is Unclear – If the user’s response is vague, prompt them to clarify whether they have tested data speeds in different locations.
d. Do not allow moving a step further if user requests for it
e. Do not allow moving to a previous step if user requests for it

##Conditions to Determine the Next Step:
*if the user confirmed that the data speed is slow at particular places only, but he also verified the speed remain fast/normal at other areas-Step 2A.1 Move to a More Open Area to check if mobile signal improves
*if issue persists across all different geographical locations, like home, work, public spaces, outdoor, etc.-Step 2A.1 Move to a More Open Area to check if mobile signal improves
*if user wishes to continue testing at more different places (higher priority)-remain
*If the user's response is unclear-remain

---

#2A.1 Move to a More Open Area to check if mobile signal improves
##Data to Collect from the User:  
To check if mobile signal strength or data speed improves in an open environment with fewer obstructions.

##Approaches for LLM to Collect the Required Data:  
a. Instruct the User to Move to a More Open Area – Ask the user to go to a location with fewer obstacles (e.g., outdoors, near a window).  
b. Ask the User to Recheck Their Signal Strength and Data Speed – Guide the user to observe changes in network bars or data performance.  
c. Request a Confirmation on Improvement – Directly ask if the issue has been resolved or persists.
d. Do not allow moving a step further if user requests for it
e. Do allow moving to previous step if user requests for it

##Conditions to Determine the Next Step:
*if the signal does not improve or only improves slightly after moving to a more open area-Step 2A.2 Check for Provider-Side Outages 
*if the signal improves a lot after moving to a more open area-Step 50 Summary
*if the data speed does not improve or only improves slightly after moving to a more open area-Step 2A.2 Check for Provider-Side Outages
*if user requests to move to previous step-Proceed to previous step
*if the user's response is unclear-remain

---

#2B Refresh the Network Connection  
##Data to Collect from the User:  
a. Determine current signal strength (e.g., number of signal bars).  
b. Ask if the user has already tried refreshing the network connection (e.g., toggling airplane mode).  
c. Guide the user through refreshing the network connection and check if it improves the signal.  
d. Confirm whether the issue persists after refreshing the connection.

##Approaches for LLM to Collect the Required Data:  
a. Ask the User to First Check Their Signal Strength such that a comparison can be made after refreshing the network  
b. Confirm if the Signal Has Improved  
c. Instruct the User to Refresh the Network Connection – toggling Airplane Mode  
d. Do not allow moving a step further if user requests for it
e. Do allow moving to previous step if user requests for it

##Conditions to Determine the Next Step:
*if signal strength remains weak or improves slightly after refreshing network-Step 2B.3 Restart the Phone
*if signal strength or data speed improves a lot after refreshing network-Step 50 Summary
*if data speed remains slow after refreshing network-Step 2B.3 Restart the Phone  
*if user requests to move to previous step-Proceed to previous step
*if the user's response is unclear-remain

---

#2A.2 Check for Provider-Side Outages  
##Data to Collect from the User:  
a. Determine whether the issue might be caused by a network outage or service disruption from the provider.  
b. Check if the user is aware of any ongoing outages or maintenance reported by the service provider.  
c. Identify if other people nearby (family, friends, neighbors) are also experiencing similar issues.

##Approaches for LLM to Collect the Required Data:  
a. Ask the User About Known Outages – First step if user hasn't mentioned an outage.  
b. Ask the User to Check for Official Provider Updates about the outage occurance in their neighbourhood.
c. Guide the User to Check for Official Provider Updates about the outage occurance in their neighbourhood- if user does not know how to check for official announcement of outage in their area.  
d. Confirm with user if there an outage occurance in their area after they have checked for official provider update.
d. Ask if Others Nearby Are Experiencing Similar Issues – To confirm if the issue is widespread.
e. Do not allow moving a step further if user requests for it
f. Do allow moving to previous step if user requests for it

##Conditions to Determine the Next Step:  
*if user has checked the provider website and found out no official outage is announced in the user neighbourhood-Step 2B Refresh the Network Connection
*if a provider outage in the user neighbourhood is confirmed after user has checked the provider website-Step 50 Summary
*if user requests to move to previous step-Proceed to previous step
*if the user's response is unclear-remain

---

#2B.3 Restart the Phone  
##Data to Collect from the User:  
a. Confirm whether the user has already tried restarting their phone during troubleshooting.  
b. Determine whether the data speed improves after restarting or if the issue persists.

##Approaches for LLM to Collect the Required Data:  
a. Ask If the User Has Already Restarted Their Phone  
b. Guide the user to restart their phone properly and check if it improves mobile data speed.  
c. Guide the User to Observe Signal Strength After Restarting – number of signal bars on the phone's screen  
d. Confirm with user whether restarting improves slow mobile data speed.
f. Request user to restart the handphone and check the mobile speed again even if they have done it before the troubleshoot.  
e. Do not allow moving a step further if user requests for it
f. Do allow moving to previous step if user requests for it

##Conditions to Determine the Next Step:  
*if data speed remains slow or improves slightly after restarting the phone-Step 2C Plan, SIM Card, or Device Change  
*if data speed improves significantly after restarting the phone-Step 50 Summary  
*if data speed did not improve after restarting the phone-Step 2C Plan, SIM Card, or Device Change  
*if user has previously restarted the phone and it does not improve the mobile data speed-Step 2C Plan, SIM Card, or Device Change
*if user requests to move to previous step-Proceed to previous step
*if the user's response is unclear-remain
*if user requests to move to previous step-Proceed to previous step

---

#2C Plan, SIM Card, or Device Change  
##Data to Collect from the User:  
a. Check if user has recently switched phones, changed SIM cards, or updated their data plan

##Approaches for LLM to Collect the Required Data:  
a. Directly inquire if the user has recently switched devices, changed SIM cards, or modified their data plan.
b. Do not allow moving a step further if user requests for it
c. Do allow moving to previous step if user requests for it

##Conditions to Determine the Next Step:  
*if yes, users have either changed phone, SIM cards or data plan-Step 2C.1 Check Data Plan Limits  
*if users have not changed phone, SIM cards and data plan-Step 2C.1 Check Data Plan Limits  
*if user requests to move to previous step-Proceed to previous step
*if the user's response is unclear-remain

---

#2C.1 Check Data Plan Limits  
##Data to Collect from the User:  
a. Determine whether the user has reached or exceeded their data plan limit.  
b. Check if the user is experiencing reduced speeds due to a fair usage policy (FUP) or data cap.  
c. Identify whether the user is on a limited or unlimited plan and whether throttling applies.

##Approaches for LLM to Collect the Required Data:  
 a. Ask the User About Their Data Plan Usage – Directly ask if they have checked their current data usage and whether they might have reached their limit.  
b. Guide the User to Check Data Usage himself – Provide steps to check data usage via carrier apps, USSD codes, or online portals.  
c. Explain Data Throttling and Fair Usage Policies – Inform the user that some plans reduce speeds after a certain usage threshold.  
d. Guide the user to check if Fair Usage Policy is applied for their plan-You can check your plan’s Fair Usage Policy by logging into your account online or via our mobile app. Look under ‘Plan Details’ or ‘Usage Policy’.
e. Guide the user to check if the data threshold for speed reduction under Fair Usage Policy has been exceeded.
e. Confirm with user if the data threshold for speed reduction has been exceeded if Fair Usage Policy is applied on their account
f. Do not allow moving a step further if user requests for it
g. Do allow moving to previous step if user requests for it

##Conditions to Determine the Next Step:  
*if the user confirmed they do not experience throttling-Step 2C.2 Reinserting SIM  
*if the user has exceeded their data limit (remark:"close to," "almost," or "approaching," is NOT a match for exceeding)-Step 50 Summary  
*if the user experienced throttling due to exceeding of data usage limit(remark:exceeding means 100% or more data usage)-Step 50 Summary  
*if user confirmed data throttling policies or fair usage policies are applied to their account and they have exceeded the data threshold for speed reduction-Step 50 Summary    
*if data throttling policies or fair usage policies are not applied to their account-Step 2C.2 Reinserting SIM
*if data throttling policies or fair usage policies are applied to their account but they have not exceeded the data threshold for speed reduction -Step 2C.2 Reinserting SIM
*if the user has unlimited data plan-Step 2C.2 Reinserting SIM  
*if user requests to move to previous step-Proceed to previous step
*if the user's response is unclear-remain


---

#2C.2 Reinserting SIM  
##Data to Collect from the User:  
a. Determine whether the user has tried reinserting the SIM card.  
b. Check if the SIM card is properly seated and free from dust or damage.  
c. Confirm whether reinserting the SIM improves network performance.

##Approaches for LLM to Collect the Required Data:  
a. Directly inquire if the user has attempted removing and reinserting the SIM card  
b. Confirm with user if their simcard is seated properlu and free from dust or damage
b. Guide the User Through the SIM Reinsert Process:  
   i) Power off the device.  
   ii) Remove the SIM card carefully.  
   iii) Check for dust, dirt, or physical damage on the SIM card and slot.  
   iv) Reinsert the SIM securely and power the phone back on.  
   v) Ask the User to Check Network Performance After Reinsertion
c. Verify if the signal strength has improved or if the issue persists.
d. Do not allow moving a step further if user requests for it
e. Do allow moving to previous step if user requests for it

##Conditions to Determine the Next Step:  
*if reinserting the SIM card does not help-Step 2D App-Level Diagnosis  
*if reinserting the SIM card helps improve the data speed-Step 50 Summary  
*if user requests to move to previous step-Proceed to previous step
*if the user's response is unclear-remain

---

#2D App-Level Diagnosis  
##Data to Collect from the User:  
a. Determine whether the slow data issue affects all apps or only specific ones.  
b. Identify if certain apps work fine while others experience slow speeds.  
c. Check whether the issue occurs during specific activities (e.g., streaming, browsing, gaming).  
d. Verify if app updates or background data usage might be affecting performance.

##Approaches for LLM to Collect the Required Data:  
a. Ask the User If All Apps Are Affected – Directly inquire whether slow speeds occur in all apps or just certain ones.  
b. Check for Background Data Usage – Guide the user to check if apps are consuming excessive data in the background.  
c. Test Different Apps and Websites – Ask the user to try using different apps or browsers to identify if the issue is app-specific.  
d. Check for App Updates and Cache Issues – Suggest updating or clearing cache for problematic apps.
e. Do not allow moving a step further if user requests for it
f. Do allow moving to previous step if user requests for it

##Conditions to Determine the Next Step:  
*if all apps are slow-Step 2D.1.2 Test SIM Card in Another Phone  
*if only specific apps are affected-Step 2D.1.2 Test SIM Card in Another Phone  
*if user requests to move to previous step-Proceed to previous step
*if the user's response is unclear-remain
---

#2D.1.2 Test SIM Card in Another Phone  
##Data to Collect from the User:  
a. Check if the issue persists when the SIM card is inserted into another workable device.

##Approaches for LLM to Collect the Required Data:  
a. Ask the User to Insert Their SIM Card Into Another Phone – Guide them through testing the SIM in a different device.  
b. Confirm with user that the phone they’re using for testing shall be workable.
c. Check If the Issue Persists on the New Phone – Instruct the user to test data speeds after switching devices.
d. Do not allow moving a step further if user requests for it
e. Do allow moving to previous step if user requests for it

##Conditions to Determine the Next Step:  
*if user had tested the SIM card in another phone and found out the issue persists on another phone-Step 4 Escalation  
*if user had tested the SIM card in another phone and found out the SIM works fine in another phone-Step 50 Summary
*if user requests to move to previous step-Proceed to previous step
*if the user's response is unclear-remain
---

#4 Escalation  
##Data to Collect from the User:  
a. Identify if escalation to the network provider is needed.

##Approaches for LLM to Collect the Required Data:  
a. Ask the User If They Want to Escalate the Issue – Since further troubleshooting is unlikely to resolve the problem, recommend contacting the network provider or manufacturer.  
b. Provide contact number: 01x-09xx90xx
c. Do not allow moving a step further if user requests for it
d. Do allow moving to previous step if user requests for it

##Conditions to Determine the Next Step:  
*if user wants escalation-Step 50 Summary
*if user feels satisfied-Step 50 Summary
*if user requests to move to previous step-Proceed to previous step
*if the user's response is unclear-remain

---

#50 Summary  
##Data to Collect from the User:  
a. Provide a summary and analysis of user's problem
b. Check if the user wishes to close the chat or continue troubleshooting

##Approaches for LLM to Collect the Required Data:  
a. Provide a Clear Summary and Analysis 
	- Outline the troubleshooting steps taken to solve the issue
	- Detailed analysis of user problem, root cause
	- suggest solutions
b. Finally, confirm if user wish to Close the Chat or continue troubleshoot. Do not offer other options except further troubleshooting and close chat.

##Conditions to Determine the Next Step:  
*if user agrees to close chat-Step 51 Close the Chat 
*if user requests to continue troubleshooting-Revisit Previous Step
*if user requests to move to previous step-Proceed to previous step
*if the user's response is unclear-Step 51 Close the Chat




#51. Close the Chat
##Objective: 
a. End the conversation clearly and politely

##Approaches for Closing the Chat:
a. Express Appreciation
b. Provide Final Recommendations
c. Offer Future Support 
d. Politely Close the Chat

THE END








