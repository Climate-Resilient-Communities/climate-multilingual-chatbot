# Climate Chatbot Enhancement Tasks

## **RULES & GUIDELINES**
- **Priority Order**: Complete CRITICAL → HIGH → MEDIUM → LOW
- **Completion Rule**: Do not move to next task until user says "complete"
- **Always Reference**: Update this file after each task completion
- **Quality Gates**: Test each fix thoroughly before marking complete

---

## **CRITICAL Priority** 🚨

### **Task 1: Fix Spanish Language Error** 
- **Status**: ✅ COMPLETED
- **Issue**: Spanish frontend selection causes "Cannot read properties of undefined" error
- **Root Cause**: Language state disconnection between AppHeader (internal state) and main page (props expected)
- **Files Modified**:
  - ✅ `/src/webui/app/src/app/components/chat/app-header.tsx` (removed internal state, now uses props)
  - ✅ `/src/webui/app/src/app/page.tsx` (verified proper prop passing)
  - ✅ `/src/webui/app/src/lib/api.ts` (fixed error handling for API responses)
- **Test Results**: ✅ API successfully handles Spanish requests, frontend compiles without errors
- **Completion Criteria**: ✅ Spanish language selection works without errors

### **ENHANCEMENT: Smart Auto-Language Detection**
- **Status**: ✅ COMPLETED
- **Feature**: Auto-detect language when user is on English default but writes in another language
- **Logic**: Only triggers when `selectedLanguage === 'en'` AND detected language differs with >70% confidence
- **Behavior**: 
  - ✅ Auto-updates dropdown to detected language
  - ✅ Shows user-friendly notification with language name
  - ✅ User can manually override via dropdown if needed
- **Files Modified**:
  - ✅ `/src/webui/app/src/lib/api.ts` (added `detectLanguage` method and interfaces)
  - ✅ `/src/webui/app/src/app/page.tsx` (added smart detection logic)
- **Test Results**: ✅ Successfully detects Spanish with 80% confidence for longer phrases
- **Completion Criteria**: ✅ Smart language detection working as designed

### **Task 2: Climate Emergency Guardrails - Too Strict**
- **Status**: 📋 COMPLETED
- **Issue**: Users asking "help im in a climate emergency" get told to call 911 instead of helpful resources
- **Root Cause**: Input guardrail being too restrictive on emergency climate situations
- **Files to Modify**: `/src/models/input_guardrail.py`
- **Solution**: Add climate emergency keywords and appropriate response routing
- **Test Cases**: 
  - ✅"help im in a flooding emergency what can I do?"
  - ✅"climate emergency advice needed"
  - ✅"im in a climate emergency"
- **Completion Criteria**:✅ Climate emergency queries route to helpful resources, not 911

### **Task 3: Remove Success Popup Messages**
- **Status**: 📋 PENDING
- **Issue**: "Response generated successfully" toast notifications are intrusive
- **Files to Modify**: `/src/webui/app/src/app/page.tsx` (lines 123-126)
- **Solution**: Comment out or remove the success toast notification
- **Test Plan**: Send message and verify no success popup appears
- **Completion Criteria**: No more intrusive success notifications

---

## **HIGH Priority** 🔥

### **Task 4: Retry Button Double Message Bug**
- **Status**: 📋 PENDING
- **Issue**: Clicking retry shows duplicate messages instead of keeping only user question
- **Files to Modify**: 
  - `/src/webui/app/src/app/page.tsx` (handleRetry function)
  - `/src/webui/app/src/components/chat/chat-message.tsx` (retry logic)
- **Solution Options**:
  - **Option A**: Fix retry to only keep user message
  - **Option B**: Add edit functionality to user queries
- **Test Plan**: Send message, get response, click retry, verify behavior
- **Completion Criteria**: Clean retry behavior without message duplication

### **Task 5: Update Critical URLs**
- **Status**: 📋 PENDING
- **Issue**: Canada and Toronto action plan URLs need updating to newer versions
- **URLs to Update**:
  - **Canada**: `https://www.canada.ca/en/services/environment/weather/climatechange/climate-action.html`
  - **Toronto**: `https://www.toronto.ca/services-payments/water-environment/environmentally-friendly-city-initiatives/transformto/`
- **Files to Search**: Backend data files, citation sources, knowledge base
- **Solution**: Find and replace old URLs with new ones
- **Test Plan**: Query about Canada/Toronto climate action, verify new URLs appear
- **Completion Criteria**: Updated URLs appear in relevant responses


---

## **MEDIUM Priority** ⚠️

### **Task 6: Links Open in New Tab**
- **Status**: 📋 PENDING
- **Issue**: Clicking citation links should open in new tab to preserve chat session
- **Files to Modify**: Citation link components
- **Solution**: Add `target="_blank" rel="noopener noreferrer"` to external links
- **Test Plan**: Click citation link, verify new tab opens, chat remains intact
- **Completion Criteria**: All external links open in new tabs

### **Task 7: URL Liveness Check & PDF Fallback**
- **Status**: 📋 PENDING
- **Feature**: Implement URL validation with fallback to PDF
- **Requirements**:
  - Check if URL returns valid response (not 404, timeout, etc.)
  - On success: Function as normal
  - On failure: Show notification "This link appears to be broken. A PDF version is being provided as an alternative."
  - Display PDF version as fallback
  - Ensure that in the message from the Assistant the links are all valid as well
- **Files to Create/Modify**: URL validation service, citation component
- **Test Plan**: Test with broken URLs, verify fallback behavior
- **Completion Criteria**: Broken links show notification and PDF alternative


---

## **PROGRESS TRACKING**

### **Completed Tasks** ✅
- None yet

### **Current Focus** 🎯
- **Task 1**: Fix Spanish Language Error (IN PROGRESS)

### **Blocked/Issues** 🚧
- None currently

### **Notes** 📝
- User emphasized not moving to next task until they say "complete"
- All fixes must be thoroughly tested before marking complete
- Priority is CRITICAL → HIGH → MEDIUM → LOW
- Update this file after each completion

---

**Last Updated**: Initial creation  
**Next Task**: Fix Spanish Language Error (Task 1)