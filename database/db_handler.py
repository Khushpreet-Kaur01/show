# Enhanced database/db_handler.py
"""
Enhanced Database Handler with comprehensive error handling and diagnostics
"""

import logging
import json
from typing import List, Dict, Optional, Tuple
from config.settings import Config
from utils.api_handler import APIHandler
from utils.data_formatters import (
    QuestionFormatter, 
    ResponseProcessor, 
    DataValidator
)
from constants import LogMessages, ErrorMessages, APIKeys

logger = logging.getLogger('survey_analytics')


class DatabaseHandler:
    """Enhanced Database Handler with comprehensive diagnostics"""
    
    def __init__(self):
        self.api = APIHandler(
            base_url=Config.API_BASE_URL,
            api_key=Config.API_KEY,
            endpoint=Config.API_ENDPOINT
        )
        self.last_operation_details = {}
    
    def test_connection(self) -> bool:
        """Test if API connection is healthy"""
        return self.api.test_connection()
    
    def get_last_operation_details(self) -> Dict:
        """Get details from the last operation for debugging"""
        return self.last_operation_details
    
    def _analyze_questions_data(self, questions: List[Dict]) -> Dict:
        """Analyze questions data for issues with special handling for empty database"""
        analysis = {
            "total_questions": len(questions),
            "questions_with_answers": 0,
            "questions_with_correct_answers": 0,
            "data_issues": [],
            "suggestions": []
        }
        
        if not questions:
            analysis["data_issues"].append("No questions returned from API")
            analysis["suggestions"].extend([
                "✅ Database is empty - this is normal for new installations",
                "📥 Import questions into the database to get started",
                "🧪 Add sample data for testing",
                "📋 This is not an error - just no data available yet"
            ])
            return analysis
        
        # Analyze question structure
        for i, question in enumerate(questions[:5]):  # Check first 5 questions
            question_id = question.get('_id') or question.get('questionID', f'Question_{i}')
            
            # Check basic structure
            if not isinstance(question, dict):
                analysis["data_issues"].append(f"Question {i} is not a dictionary")
                continue
            
            # Check ID field
            if '_id' not in question and 'questionID' not in question:
                analysis["data_issues"].append(f"Question {question_id}: Missing ID field")
            
            # Check answers
            if 'answers' not in question:
                analysis["data_issues"].append(f"Question {question_id}: Missing answers field")
            elif question['answers'] is None:
                analysis["data_issues"].append(f"Question {question_id}: Answers is null")
            elif not isinstance(question['answers'], list):
                analysis["data_issues"].append(f"Question {question_id}: Answers is not a list")
            else:
                analysis["questions_with_answers"] += 1
                
                # Check answer structure
                answers = question['answers']
                has_correct = False
                
                for j, answer in enumerate(answers[:2]):  # Check first 2 answers
                    if not isinstance(answer, dict):
                        analysis["data_issues"].append(f"Question {question_id}, Answer {j}: Not a dictionary")
                        continue
                    
                    # Check required fields
                    if 'answer' not in answer:
                        analysis["data_issues"].append(f"Question {question_id}, Answer {j}: Missing 'answer' field")
                    if 'isCorrect' not in answer:
                        analysis["data_issues"].append(f"Question {question_id}, Answer {j}: Missing 'isCorrect' field")
                    elif answer.get('isCorrect'):
                        has_correct = True
                    
                    # Check data types
                    if 'isCorrect' in answer and not isinstance(answer['isCorrect'], bool):
                        analysis["data_issues"].append(f"Question {question_id}, Answer {j}: isCorrect must be boolean, got {type(answer['isCorrect'])}")
                    
                    if 'responseCount' in answer and not isinstance(answer['responseCount'], (int, float)):
                        analysis["data_issues"].append(f"Question {question_id}, Answer {j}: responseCount must be number, got {type(answer['responseCount'])}")
                
                if has_correct:
                    analysis["questions_with_correct_answers"] += 1
        
        # Generate suggestions based on issues found
        if analysis["data_issues"]:
            analysis["suggestions"].extend([
                "🔍 Data structure issues detected - this explains your API errors!",
                "✅ The API is working, but the data format is causing processing failures",
                "🔄 Consider clearing and reimporting questions with correct structure",
                "📋 Check your data import/export process for consistency"
            ])
        elif analysis["total_questions"] > 0:
            analysis["suggestions"].extend([
                "✅ Data structure looks good",
                "📊 Questions are properly formatted",
                "🎯 Ready for ranking operations"
            ])
        
        return analysis
    
    def fetch_all_questions(self) -> List[Dict]:
        """Fetch all questions from API endpoint with clean logging"""
        try:
            logger.info("📥 Fetching questions from API...")
            
            response_data = self.api.make_request("GET")
            
            # Check if this was an empty database 404 that got converted
            if response_data.get("_empty_database"):
                logger.info("📭 Database is empty")
                self.last_operation_details = {
                    "operation": "fetch_questions",
                    "success": True,
                    "empty_database": True,
                    "analysis": {
                        "total_questions": 0,
                        "suggestions": ["Database is empty - import questions to get started"]
                    }
                }
                return []
            
            questions = ResponseProcessor.extract_questions_from_response(response_data)
            
            # Analyze the data we got
            analysis = self._analyze_questions_data(questions)
            self.last_operation_details = {
                "operation": "fetch_questions",
                "success": True,
                "analysis": analysis
            }
            
            # Log summary
            logger.info(f"✅ Found {analysis['total_questions']} questions")
            if analysis['questions_with_correct_answers'] > 0:
                logger.info(f"🎯 {analysis['questions_with_correct_answers']} questions ready for ranking")
            
            # Only show data issues if they exist
            if analysis["data_issues"]:
                logger.warning(f"⚠️ {len(analysis['data_issues'])} data issues detected")
                if logger.isEnabledFor(logging.DEBUG):
                    for issue in analysis["data_issues"][:3]:
                        logger.debug(f"   • {issue}")
            
            # Process questions for internal use
            processed_questions = self._process_fetched_questions(questions)
            return processed_questions
            
        except Exception as e:
            # Check if this is actually a 404 that should be treated as empty database
            if "404" in str(e) or "not found" in str(e).lower():
                logger.info("📭 No questions found - database is empty")
                self.last_operation_details = {
                    "operation": "fetch_questions",
                    "success": True,
                    "empty_database": True
                }
                return []
            
            self.last_operation_details = {
                "operation": "fetch_questions",
                "success": False,
                "error": str(e)
            }
            
            logger.error(f"❌ Failed to fetch questions: {str(e)}")
            raise
    
    def _process_fetched_questions(self, questions: List[Dict]) -> List[Dict]:
        """Process raw questions from API for internal use"""
        processed_questions = []
        processing_issues = []
        
        for i, question in enumerate(questions):
            try:
                processed_question = QuestionFormatter.ensure_compatibility(question)
                processed_questions.append(processed_question)
            except Exception as e:
                question_id = question.get('_id', f'Question_{i}')
                processing_issues.append(f"Question {question_id}: {str(e)}")
                logger.warning(f"Failed to process question {question_id}: {str(e)}")
        
        if processing_issues:
            logger.warning(f"⚠️ {len(processing_issues)} questions had processing issues:")
            for issue in processing_issues[:3]:  # Show first 3
                logger.warning(f"  • {issue}")
        
        return processed_questions
    
    def update_question_answers(self, question_id: str, answers: List[Dict]) -> bool:
        """Update answers for a specific question via API"""
        try:
            logger.info(f"📤 Updating question {question_id} with {len(answers)} answers")
            
            target_question = self._find_question_by_id(question_id)
            if not target_question:
                logger.error(f"❌ Question {question_id} not found")
                return False
            
            # Validate answers before update
            validation_result = self._validate_answers_for_update(answers, question_id)
            if not validation_result["valid"]:
                logger.error(f"❌ Answer validation failed for question {question_id}:")
                for error in validation_result["errors"][:3]:
                    logger.error(f"  • {error}")
                return False
            
            # Update the question with new answers
            target_question[Config.QuestionFields.ANSWERS] = answers
            
            # Format for API submission
            update_data = self._build_single_question_payload(target_question)
            
            logger.debug(f"Updating question {question_id} with validated data")
            
            # Make API request
            response = self.api.make_request("PUT", update_data)
            
            # Check if update was successful
            if ResponseProcessor.is_success_response(response):
                logger.info(f"✅ Successfully updated question {question_id}")
                return True
            else:
                error_msg = response.get(APIKeys.MESSAGE, str(response))
                logger.error(f"❌ Update failed for question {question_id}: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Exception updating question {question_id}: {str(e)}")
            return False
    
    def _validate_answers_for_update(self, answers: List[Dict], question_id: str) -> Dict:
        """Validate answers before update"""
        errors = []
        
        if not answers:
            errors.append("No answers provided")
            return {"valid": False, "errors": errors}
        
        for i, answer in enumerate(answers):
            if not isinstance(answer, dict):
                errors.append(f"Answer {i}: Must be a dictionary")
                continue
            
            # Check required fields
            if 'answer' not in answer:
                errors.append(f"Answer {i}: Missing 'answer' field")
            if 'isCorrect' not in answer:
                errors.append(f"Answer {i}: Missing 'isCorrect' field")
            
            # Check data types
            if 'isCorrect' in answer and not isinstance(answer['isCorrect'], bool):
                errors.append(f"Answer {i}: 'isCorrect' must be boolean, got {type(answer['isCorrect'])}")
            
            if 'responseCount' in answer and not isinstance(answer['responseCount'], (int, float)):
                errors.append(f"Answer {i}: 'responseCount' must be number, got {type(answer['responseCount'])}")
        
        return {"valid": len(errors) == 0, "errors": errors}
    
    def _find_question_by_id(self, question_id: str) -> Dict:
        """Find question by ID from API"""
        questions = self.fetch_all_questions()
        
        for question in questions:
            if (question.get('_id') == question_id or 
                question.get('questionID') == question_id):
                return question
        
        return None
    
    def _build_single_question_payload(self, question: Dict) -> Dict:
        """Build API payload for single question update"""
        formatted_question = QuestionFormatter.format_for_api(question)
        return {APIKeys.QUESTIONS: [formatted_question]}
    
    def bulk_update_questions(self, questions: List[Dict]) -> Dict:
        """Bulk update multiple questions via single API call with enhanced validation"""
        try:
            logger.info(f"📤 Starting bulk update of {len(questions)} questions")
            
            # Enhanced validation before update
            validation_result = self._validate_questions_for_bulk_update(questions)
            
            if validation_result["invalid_count"] > 0:
                logger.warning(f"⚠️ Validation issues found:")
                logger.warning(f"  Valid questions: {validation_result['valid_count']}")
                logger.warning(f"  Invalid questions: {validation_result['invalid_count']}")
                
                # Log first few validation errors
                for error in validation_result["validation_errors"][:5]:
                    logger.warning(f"  • {error}")
                
                if validation_result["valid_count"] == 0:
                    logger.error("❌ No valid questions to update")
                    return self._create_update_result(0, len(questions), len(questions))
            
            valid_questions = validation_result["valid_questions"]
            logger.info(f"📋 Proceeding with {len(valid_questions)} valid questions")
            
            # Perform bulk update
            return self._execute_bulk_update(valid_questions, len(questions))
            
        except Exception as e:
            logger.error(f"❌ Bulk update failed: {str(e)}")
            self.last_operation_details = {
                "operation": "bulk_update",
                "success": False,
                "error": str(e),
                "question_count": len(questions)
            }
            raise
    
    def _validate_questions_for_bulk_update(self, questions: List[Dict]) -> Dict:
        """Validate questions before bulk update with detailed reporting"""
        valid_questions = []
        validation_errors = []
        
        logger.debug(f"🔍 Validating {len(questions)} questions for bulk update")
        
        for i, question in enumerate(questions):
            question_id = QuestionFormatter.get_question_id(question)
            
            # Basic structure validation
            if not question_id or question_id == 'UNKNOWN':
                validation_errors.append(f"Question {i}: Missing or invalid ID")
                continue
            
            # Check if question has answers
            if not question.get('answers'):
                validation_errors.append(f"Question {question_id}: No answers")
                continue
            
            # Validate answer structure
            answer_validation = self._validate_question_answers_bulk(question, question_id)
            if not answer_validation["valid"]:
                validation_errors.extend(answer_validation["errors"])
                continue
            
            # Additional business logic validation
            if not DataValidator.validate_question(question):
                validation_errors.append(f"Question {question_id}: Failed business logic validation")
                continue
            
            valid_questions.append(question)
            logger.debug(f"✅ Question {question_id} passed validation")
        
        return {
            "valid_questions": valid_questions,
            "valid_count": len(valid_questions),
            "invalid_count": len(questions) - len(valid_questions),
            "validation_errors": validation_errors
        }
    
    def _validate_question_answers_bulk(self, question: Dict, question_id: str) -> Dict:
        """Validate individual question's answers for bulk update"""
        errors = []
        answers = question.get('answers', [])
        
        for i, answer in enumerate(answers):
            if not isinstance(answer, dict):
                errors.append(f"Question {question_id}, Answer {i}: Not a dictionary")
                continue
            
            # Check required fields
            required_fields = ['answer', 'isCorrect']
            for field in required_fields:
                if field not in answer:
                    errors.append(f"Question {question_id}, Answer {i}: Missing '{field}' field")
            
            # Check data types
            if 'isCorrect' in answer and not isinstance(answer['isCorrect'], bool):
                errors.append(f"Question {question_id}, Answer {i}: 'isCorrect' must be boolean")
            
            if 'responseCount' in answer and not isinstance(answer['responseCount'], (int, float)):
                errors.append(f"Question {question_id}, Answer {i}: 'responseCount' must be number")
            
            # Check for common data corruption issues
            if 'rank' in answer and not isinstance(answer['rank'], (int, float)):
                errors.append(f"Question {question_id}, Answer {i}: 'rank' must be number")
            
            if 'score' in answer and not isinstance(answer['score'], (int, float)):
                errors.append(f"Question {question_id}, Answer {i}: 'score' must be number")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _execute_bulk_update(self, formatted_questions: List[Dict], original_count: int) -> Dict:
        """Execute the bulk update API call with enhanced error handling"""
        try:
            logger.info(f"🚀 Executing bulk update for {len(formatted_questions)} questions")
            
            # Prepare update payload
            valid_formatted = []
            for question in formatted_questions:
                try:
                    formatted_question = QuestionFormatter.format_for_api(question)
                    valid_formatted.append(formatted_question)
                except Exception as e:
                    question_id = QuestionFormatter.get_question_id(question)
                    logger.error(f"Failed to format question {question_id}: {str(e)}")
            
            if not valid_formatted:
                logger.error("❌ No questions could be formatted for API")
                return self._create_update_result(0, len(formatted_questions), original_count)
            
            bulk_update_data = {APIKeys.QUESTIONS: valid_formatted}
            
            # Log payload summary
            logger.info(f"📦 Sending {len(valid_formatted)} formatted questions to API")
            logger.debug(f"Sample question structure: {json.dumps(valid_formatted[0], indent=2, default=str)[:300]}...")
            
            # Make the API request
            response = self.api.make_request("PUT", bulk_update_data)
            
            # Analyze response
            if ResponseProcessor.is_success_response(response):
                updated_count = len(valid_formatted)
                logger.info(f"✅ Bulk update successful: {updated_count} questions updated")
                
                self.last_operation_details = {
                    "operation": "bulk_update",
                    "success": True,
                    "updated_count": updated_count,
                    "original_count": original_count,
                    "response_preview": str(response)[:200]
                }
                
                return self._create_update_result(updated_count, 0, original_count)
            else:
                error_msg = response.get(APIKeys.MESSAGE, str(response))
                logger.error(f"❌ Bulk update failed: {error_msg}")
                logger.error(f"Response: {response}")
                
                self.last_operation_details = {
                    "operation": "bulk_update",
                    "success": False,
                    "error": error_msg,
                    "response": response
                }
                
                return self._create_update_result(0, len(valid_formatted), original_count)
                
        except Exception as e:
            logger.error(f"❌ Bulk update execution failed: {str(e)}")
            
            self.last_operation_details = {
                "operation": "bulk_update",
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            
            return self._create_update_result(0, len(formatted_questions), original_count)
    
    def _create_update_result(self, updated: int, failed: int, total: int) -> Dict:
        """Create standardized update result dictionary"""
        return {
            "updated_count": updated,
            "failed_count": failed,
            "total_processed": total
        }
    
    def submit_final_questions(self, questions: List[Dict]) -> Dict:
        """Submit final ranked questions to the final endpoint with update logic for existing questions"""
        try:
            logger.info("🏆 Starting final submission process with update logic...")
            
            # Filter and format questions for final submission
            final_questions = self._prepare_questions_for_final_submission(questions)
            
            if not final_questions:
                logger.warning("📭 No questions ready for final submission")
                return {
                    "submitted_count": 0,
                    "total_processed": len(questions),
                    "success": False,
                    "message": "No questions with ranked correct answers found"
                }
            
            # Check for existing questions in final collection and handle updates
            submission_result = self._handle_final_submission_with_updates(final_questions)
            
            return submission_result
            
        except Exception as e:
            logger.error(f"❌ Final submission failed with exception: {str(e)}")
            
            self.last_operation_details = {
                "operation": "final_submission",
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            
            return {
                "submitted_count": 0,
                "total_processed": len(questions),
                "success": False,
                "error": str(e)
            }

    def _handle_final_submission_with_updates(self, final_questions: List[Dict]) -> Dict:
        """Handle final submission with logic to update existing questions if answers changed"""
        try:
            # First, get existing final collection to check for duplicates
            existing_final_questions = self._get_existing_final_questions()
            
            if existing_final_questions is None:
                logger.warning("⚠️ Could not retrieve existing final collection, proceeding with normal submission")
                return self._submit_new_final_questions(final_questions)
            
            # Categorize questions: new vs existing with changes
            new_questions, updated_questions, unchanged_questions = self._categorize_questions_for_submission(
                final_questions, existing_final_questions
            )
            
            logger.info(f"📊 Final submission analysis:")
            logger.info(f"   📝 New questions: {len(new_questions)}")
            logger.info(f"   🔄 Questions with changes: {len(updated_questions)}")
            logger.info(f"   ✅ Unchanged questions: {len(unchanged_questions)}")
            
            total_submitted = 0
            success_messages = []
            
            # Submit new questions
            if new_questions:
                new_result = self._submit_new_final_questions(new_questions)
                if new_result.get("success"):
                    total_submitted += new_result["submitted_count"]
                    success_messages.append(f"{new_result['submitted_count']} new questions submitted")
                else:
                    logger.error(f"❌ Failed to submit new questions: {new_result.get('message', 'Unknown error')}")
            
            # Update existing questions with changes
            if updated_questions:
                update_result = self._update_existing_final_questions(updated_questions)
                if update_result.get("success"):
                    total_submitted += update_result["submitted_count"]
                    success_messages.append(f"{update_result['submitted_count']} questions updated")
                else:
                    logger.error(f"❌ Failed to update existing questions: {update_result.get('message', 'Unknown error')}")
            
            # Report unchanged questions
            if unchanged_questions:
                logger.info(f"ℹ️ {len(unchanged_questions)} questions unchanged, skipped submission")
            
            # Prepare final result
            overall_success = total_submitted > 0 or len(unchanged_questions) > 0
            message = "; ".join(success_messages) if success_messages else "No changes detected"
            
            if overall_success:
                logger.info(f"✅ Final submission completed: {message}")
            
            return {
                "submitted_count": total_submitted,
                "total_processed": len(final_questions),
                "success": overall_success,
                "message": message,
                "details": {
                    "new_submitted": len(new_questions) if new_questions else 0,
                    "updated": len(updated_questions) if updated_questions else 0,
                    "unchanged": len(unchanged_questions)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in final submission with updates: {str(e)}")
            return {
                "submitted_count": 0,
                "total_processed": len(final_questions),
                "success": False,
                "error": str(e)
            }

    def _get_existing_final_questions(self) -> Optional[List[Dict]]:
        """Get existing questions from final collection"""
        try:
            final_api = APIHandler(
                base_url=Config.API_BASE_URL,
                api_key=Config.API_KEY,
                endpoint="/api/v1/admin/survey/final"
            )
            
            response = final_api.make_request("GET")
            
            if ResponseProcessor.is_success_response(response):
                existing_questions = ResponseProcessor.extract_questions_from_response(response)
                logger.info(f"📋 Found {len(existing_questions)} existing questions in final collection")
                return existing_questions
            else:
                logger.warning("⚠️ Could not retrieve final collection")
                return None
                
        except Exception as e:
            logger.warning(f"⚠️ Error retrieving final collection: {str(e)}")
            return None

    def _categorize_questions_for_submission(self, final_questions: List[Dict], existing_final_questions: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Categorize questions as new, updated, or unchanged"""
        new_questions = []
        updated_questions = []
        unchanged_questions = []
        
        # Create lookup of existing questions by question text (case insensitive)
        existing_lookup = {}
        for existing in existing_final_questions:
            question_text = existing.get('question', '').strip().lower()
            if question_text:
                existing_lookup[question_text] = existing
        
        for question in final_questions:
            question_text = question.get('question', '').strip().lower()
            question_id = QuestionFormatter.get_question_id(question)
            
            if question_text in existing_lookup:
                existing_question = existing_lookup[question_text]
                
                # Compare answers to see if there are changes
                if self._answers_have_changed(question, existing_question):
                    # Add the existing question ID for update
                    question['_existing_id'] = existing_question.get('_id')
                    updated_questions.append(question)
                    logger.info(f"🔄 Question '{question_text[:50]}...' has answer changes, will update")
                else:
                    unchanged_questions.append(question)
                    logger.info(f"✅ Question '{question_text[:50]}...' unchanged, skipping")
            else:
                new_questions.append(question)
                logger.info(f"📝 Question '{question_text[:50]}...' is new, will submit")
        
        return new_questions, updated_questions, unchanged_questions

    def _answers_have_changed(self, new_question: Dict, existing_question: Dict) -> bool:
        """Compare answers between new and existing questions to detect changes"""
        new_answers = new_question.get('answers', [])
        existing_answers = existing_question.get('answers', [])
        
        # Quick check: different number of answers
        if len(new_answers) != len(existing_answers):
            logger.debug(f"Answer count changed: {len(existing_answers)} -> {len(new_answers)}")
            return True
        
        # Create normalized answer comparison
        def normalize_answer_for_comparison(answer):
            return {
                'answer': str(answer.get('answer', '')).strip().lower(),
                'isCorrect': bool(answer.get('isCorrect', False)),
                'rank': int(answer.get('rank', 0)),
                'score': int(answer.get('score', 0)),
                'responseCount': int(answer.get('responseCount', 0))
            }
        
        # Normalize and sort answers for comparison
        new_normalized = sorted([normalize_answer_for_comparison(a) for a in new_answers], 
                            key=lambda x: (x['answer'], x['rank']))
        existing_normalized = sorted([normalize_answer_for_comparison(a) for a in existing_answers], 
                                    key=lambda x: (x['answer'], x['rank']))
        
        # Compare normalized answers
        if new_normalized != existing_normalized:
            logger.debug("Answer content, rankings, or scores have changed")
            return True
        
        logger.debug("No significant changes detected in answers")
        return False

    def _submit_new_final_questions(self, new_questions: List[Dict]) -> Dict:
        """Submit completely new questions to final collection"""
        logger.info(f"📤 Submitting {len(new_questions)} new questions to final endpoint")
        
        # Prepare payload
        final_payload = {"questions": new_questions}
        
        # Log payload for debugging
        logger.debug("🔍 New questions payload:")
        logger.debug(json.dumps(final_payload, indent=2, default=str)[:500] + "...")
        
        # Create final API handler
        final_api = APIHandler(
            base_url=Config.API_BASE_URL,
            api_key=Config.API_KEY,
            endpoint="/api/v1/admin/survey/final"
        )
        
        # Make the submission
        response = final_api.make_request("POST", final_payload)
        
        # Check response
        if ResponseProcessor.is_success_response(response):
            logger.info(f"✅ Successfully submitted {len(new_questions)} new questions")
            return {
                "submitted_count": len(new_questions),
                "success": True,
                "message": f"Submitted {len(new_questions)} new questions"
            }
        else:
            error_msg = response.get("message", str(response))
            logger.error(f"❌ Failed to submit new questions: {error_msg}")
            return {
                "submitted_count": 0,
                "success": False,
                "message": error_msg
            }

    def _update_existing_final_questions(self, updated_questions: List[Dict]) -> Dict:
        """Update existing questions in final collection"""
        logger.info(f"🔄 Updating {len(updated_questions)} existing questions in final collection")
        
        successful_updates = 0
        
        for question in updated_questions:
            question_id = question.get('_existing_id')
            question_text = question.get('question', '')[:50]
            
            if not question_id:
                logger.error(f"❌ No existing ID found for question '{question_text}...'")
                continue
            
            # Prepare single question update
            update_payload = {"questions": [question]}
            
            # Try to update via PUT to the specific question endpoint
            success = self._update_single_final_question(question_id, update_payload)
            
            if success:
                successful_updates += 1
                logger.info(f"✅ Updated question '{question_text}...'")
            else:
                logger.error(f"❌ Failed to update question '{question_text}...'")
        
        if successful_updates > 0:
            logger.info(f"✅ Successfully updated {successful_updates}/{len(updated_questions)} questions")
        
        return {
            "submitted_count": successful_updates,
            "success": successful_updates > 0,
            "message": f"Updated {successful_updates} of {len(updated_questions)} questions"
        }

    def _update_single_final_question(self, question_id: str, update_payload: Dict) -> bool:
        """Update a single question in final collection"""
        try:
            # Try different update approaches
            update_endpoints = [
                f"/api/v1/admin/survey/final/{question_id}",  # RESTful update
                "/api/v1/admin/survey/final",                  # Bulk update
            ]
            
            for endpoint in update_endpoints:
                try:
                    final_api = APIHandler(
                        base_url=Config.API_BASE_URL,
                        api_key=Config.API_KEY,
                        endpoint=endpoint
                    )
                    
                    # Try PUT first, then PATCH
                    for method in ["PUT", "PATCH"]:
                        try:
                            response = final_api.make_request(method, update_payload)
                            
                            if ResponseProcessor.is_success_response(response):
                                logger.debug(f"✅ Updated via {method} {endpoint}")
                                return True
                            else:
                                logger.debug(f"❌ {method} {endpoint} failed: {response.get('message', 'Unknown error')}")
                        except Exception as method_error:
                            logger.debug(f"❌ {method} {endpoint} error: {str(method_error)}")
                            continue
                            
                except Exception as endpoint_error:
                    logger.debug(f"❌ Endpoint {endpoint} error: {str(endpoint_error)}")
                    continue
            
            # If all update attempts fail, log detailed error
            logger.warning(f"⚠️ All update methods failed for question {question_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error updating question {question_id}: {str(e)}")
            return False
        # Updated method for database/db_handler.py - Test with Input questions only

    def _prepare_questions_for_final_submission(self, questions: List[Dict]) -> List[Dict]:
        """Prepare questions for final submission - ONLY Input type questions (based on debug evidence)"""
        final_questions = []
        
        for question in questions:
            question_id = QuestionFormatter.get_question_id(question)
            question_type = question.get('questionType', '').lower()
            
            # BASED ON DEBUG EVIDENCE: Only Input type questions for final submission
            # MCQ questions return 400 Bad Request, Input questions get 500 (pass validation)
            if question_type != 'input':
                logger.info(f"⏭️ Skipping question {question_id} - Only Input type questions submitted to final (Type: {question.get('questionType', '')})")
                continue
            
            # Check if question has answers
            if not question.get('answers'):
                logger.debug(f"Skipping question {question_id} - no answers")
                continue
            
            # Validate based on question type and server requirements
            should_include, final_answers = self._validate_and_prepare_answers_for_final(question, question_id, question_type)
            
            # Include question if it meets the requirements
            if should_include and final_answers:
                final_question = {
                    "question": str(question.get('question', '')),  # Ensure string
                    "questionType": str(question.get('questionType', '')),  # Ensure string
                    "questionCategory": str(question.get('questionCategory', '')),  # Ensure string
                    "questionLevel": str(question.get('questionLevel', '')),  # Ensure string
                    "timesSkipped": int(question.get('timesSkipped', 0)),  # Ensure integer
                    "timesAnswered": int(question.get('timesAnswered', 0)),  # Ensure integer
                    "answers": final_answers
                }
                final_questions.append(final_question)
            else:
                logger.debug(f"⏭️ Skipping {question_type} question {question_id} - server requirements not met")
        
        logger.info(f"📋 Prepared {len(final_questions)} Input questions for final submission")
        
        if len(final_questions) > 0:
            logger.info(f"   📝 Input questions: {len(final_questions)} (exactly 3 correct answers each)")
        else:
            logger.warning("⚠️ No Input questions ready for final submission")
            logger.info("💡 Note: Debug evidence shows only Input questions are accepted by final endpoint")
            logger.info("💡 MCQ questions return 400 Bad Request - they may not be supported in final collection")
        
        return final_questions

    def _validate_and_prepare_answers_for_final(self, question: Dict, question_id: str, question_type: str) -> Tuple[bool, List[Dict]]:
        """Validate and prepare answers according to server requirements"""
        
        all_answers = question.get('answers', [])
        
        if question_type == 'input':
            return self._prepare_input_question_for_final(question_id, all_answers)
        elif question_type == 'mcq':
            return self._prepare_mcq_question_for_final(question_id, all_answers)
        
        return False, []

    def _prepare_input_question_for_final(self, question_id: str, all_answers: List[Dict]) -> Tuple[bool, List[Dict]]:
        """Prepare Input question according to server requirements:
        - Must have at least 3 valid answers
        - Must have exactly 3 correct answers
        - Only correct answers are kept
        """
        
        # Filter to only correct answers with rank > 0 and score > 0
        correct_answers = []
        for answer in all_answers:
            if (answer.get('isCorrect') is True and 
                answer.get('rank', 0) > 0 and 
                answer.get('score', 0) > 0):
                correct_answers.append(answer)
        
        # Server requirement: exactly 3 correct answers for Input questions
        if len(correct_answers) < 3:
            logger.warning(f"⚠️ Skipping Input question {question_id} - needs minimum 3 correct answers, found {len(correct_answers)}")
            return False, []
        
        # Take only the top 3 correct answers (sorted by rank)
        correct_answers.sort(key=lambda x: x.get('rank', 999))
        top_3_answers = correct_answers[:3]
        
        # Format answers for final submission
        final_answers = []
        for answer in top_3_answers:
            final_answer = {
                "answer": str(answer.get('answer', '')).strip(),  # Ensure string and trim
                "responseCount": int(answer.get('responseCount', 0)),  # Ensure integer
                "isCorrect": True,  # Always true for final submission
                "rank": int(answer.get('rank', 0)),  # Ensure integer
                "score": int(answer.get('score', 0))  # Ensure integer
            }
            
            # Server validation: answer must not be empty
            if not final_answer["answer"]:
                logger.warning(f"⚠️ Skipping Input question {question_id} - has empty answer")
                return False, []
                
            final_answers.append(final_answer)
        
        logger.info(f"✅ Input question {question_id} ready for final submission with exactly 3 correct answers")
        return True, final_answers

    def _prepare_mcq_question_for_final(self, question_id: str, all_answers: List[Dict]) -> Tuple[bool, List[Dict]]:
        """Prepare MCQ question according to server requirements:
        - Must have exactly 4 answer options
        - Must have exactly 1 correct answer
        - Each answer must have non-empty text
        - Answer options must be unique
        - ALL answers (correct and incorrect) are included
        """
        
        # Server requirement: exactly 4 answers for MCQ
        if len(all_answers) != 4:
            logger.warning(f"⚠️ Skipping MCQ question {question_id} - needs exactly 4 answer options, found {len(all_answers)}")
            return False, []
        
        # Count correct answers
        correct_answers = [a for a in all_answers if a.get('isCorrect') is True]
        
        # Server requirement: exactly 1 correct answer
        if len(correct_answers) != 1:
            logger.warning(f"⚠️ Skipping MCQ question {question_id} - needs exactly 1 correct answer, found {len(correct_answers)}")
            return False, []
        
        # Check for empty answers and duplicates
        answer_texts = []
        for answer in all_answers:
            answer_text = str(answer.get('answer', '')).strip()
            
            # Server validation: each answer must have non-empty text
            if not answer_text:
                logger.warning(f"⚠️ Skipping MCQ question {question_id} - has empty answer text")
                return False, []
            
            answer_texts.append(answer_text.lower())
        
        # Server validation: answer options must be unique
        if len(set(answer_texts)) != len(answer_texts):
            logger.warning(f"⚠️ Skipping MCQ question {question_id} - answer options must be unique")
            return False, []
        
        # Format all answers for final submission (including incorrect ones)
        final_answers = []
        for answer in all_answers:
            final_answer = {
                "answer": str(answer.get('answer', '')).strip(),  # Ensure string and trim
                "responseCount": int(answer.get('responseCount', 0)),  # Ensure integer
                "isCorrect": bool(answer.get('isCorrect', False)),  # Preserve correct/incorrect
                "rank": int(answer.get('rank', 0)),  # Ensure integer
                "score": int(answer.get('score', 0))  # Ensure integer
            }
            final_answers.append(final_answer)
        
        logger.info(f"✅ MCQ question {question_id} ready for final submission with 4 options and 1 correct answer")
        return True, final_answers
    
    def get_diagnostic_summary(self) -> Dict:
        """Get comprehensive diagnostic information"""
        summary = {
            "api_config": {
                "base_url": Config.API_BASE_URL,
                "endpoint": Config.API_ENDPOINT,
                "api_key_preview": f"{Config.API_KEY[:8]}..." if Config.API_KEY else "Not set"
            },
            "last_operation": self.last_operation_details,
            "connection_status": "unknown"
        }
        
        # Test connection
        try:
            is_connected = self.test_connection()
            summary["connection_status"] = "healthy" if is_connected else "failed"
        except Exception as e:
            summary["connection_status"] = f"error: {str(e)}"
        
        # Get sample data for analysis
        try:
            logger.info("🔍 Getting sample data for diagnostic analysis...")
            questions = self.fetch_all_questions()
            analysis = self._analyze_questions_data(questions)
            summary["data_analysis"] = analysis
        except Exception as e:
            summary["data_analysis"] = {"error": str(e)}
        
        return summary
    
    def debug_api_issues(self) -> Dict:
        """Comprehensive API debugging with clean output"""
        logger.info("🔍 Running API diagnostics...")
        
        debug_results = {
            "connection_test": {},
            "data_fetch_test": {},
            "data_analysis": {},
            "recommendations": []
        }
        
        # 1. Test connection
        logger.info("Testing connection...")
        try:
            connection_success = self.test_connection()
            debug_results["connection_test"] = {"success": connection_success}
            
            if not connection_success:
                debug_results["recommendations"].append("Fix API connection before proceeding")
                logger.error("❌ Connection test failed")
                return debug_results
                
        except Exception as e:
            debug_results["connection_test"] = {"success": False, "error": str(e)}
            logger.error(f"❌ Connection test error: {str(e)}")
            return debug_results
        
        # 2. Test data fetch
        logger.info("Testing data fetch...")
        try:
            questions = self.fetch_all_questions()
            debug_results["data_fetch_test"] = {
                "success": True,
                "question_count": len(questions),
                "empty_database": len(questions) == 0
            }
            
            # 3. Analyze data
            analysis = self._analyze_questions_data(questions)
            debug_results["data_analysis"] = analysis
            
            # Generate clean recommendations
            if len(questions) == 0:
                debug_results["recommendations"] = [
                    "✅ Database is empty - this is normal for new installations",
                    "📥 Import questions to start using the system"
                ]
                logger.info("✅ Empty database detected - ready for data import")
            elif analysis["data_issues"]:
                debug_results["recommendations"] = [
                    "🔍 Data structure issues found",
                    "🔄 Consider clearing and reimporting data with correct format"
                ]
                logger.warning("⚠️ Data structure issues detected")
            else:
                debug_results["recommendations"] = ["✅ System ready for operation"]
                logger.info("✅ All checks passed")
                
        except Exception as e:
            debug_results["data_fetch_test"] = {"success": False, "error": str(e)}
            
            if "404" in str(e) or "not found" in str(e).lower():
                debug_results["recommendations"] = [
                    "📭 Database appears to be empty",
                    "✅ This is normal - not an error"
                ]
                logger.info("✅ Empty database confirmed")
            else:
                debug_results["recommendations"] = [f"❌ Data fetch failed: {str(e)}"]
                logger.error(f"❌ Data fetch failed: {str(e)}")
        
        # Summary
        logger.info("📋 Diagnostic summary:")
        for i, rec in enumerate(debug_results["recommendations"], 1):
            logger.info(f"   {i}. {rec}")
        
        return debug_results
    
    def close(self):
        """Close API connection (no-op for REST API)"""
        logger.info("Enhanced database handler closed")
    
    def discover_correct_endpoint(self) -> Dict[str, any]:
        """Since there's only one endpoint, this will test server status instead"""
        logger.info("🔍 TESTING SERVER STATUS")
        logger.info("=" * 50)
        logger.info(f"Testing confirmed endpoint: {self.api.endpoint}")
        
        result = {
            "endpoint": self.api.endpoint,
            "server_responsive": False,
            "error_details": None,
            "recommendations": []
        }
        
        try:
            # Test base URL first
            import requests
            base_response = requests.get(self.api.base_url, timeout=10)
            logger.info(f"✅ Base server is responding (status: {base_response.status_code})")
            result["server_responsive"] = True
            
            # Now test the specific endpoint
            try:
                response_data = self.api.make_request("GET")
                logger.info("✅ Endpoint is working!")
                result["endpoint_working"] = True
            except Exception as endpoint_error:
                logger.error(f"❌ Endpoint failed: {str(endpoint_error)}")
                result["endpoint_working"] = False
                result["error_details"] = str(endpoint_error)
                result["recommendations"] = [
                    "Server is running but endpoint is not available",
                    "Check if endpoint is properly registered on server",
                    "Verify server deployment completed successfully",
                    "Contact server administrator about endpoint configuration"
                ]
        
        except Exception as server_error:
            logger.error(f"❌ Base server not responding: {str(server_error)}")
            result["server_responsive"] = False
            result["error_details"] = str(server_error)
            result["recommendations"] = [
                "Server appears to be down or unreachable",
                "Check server status and deployment",
                "Verify network connectivity",
                "Contact server administrator"
            ]
        
        # Log recommendations
        if result["recommendations"]:
            logger.info("💡 RECOMMENDATIONS:")
            for rec in result["recommendations"]:
                logger.info(f"   • {rec}")
        
        return result