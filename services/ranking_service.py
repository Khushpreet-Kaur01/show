"""
Enhanced Ranking Service - Complete with Final Submission Integration for Input Only
"""

import logging
from typing import List, Dict, Tuple
from config.settings import Config
from utils.data_formatters import QuestionFormatter, DataValidator
from constants import AnswerFields, LogMessages, ErrorMessages

logger = logging.getLogger('survey_analytics')


class AnswerRanker:
    """Handles the core ranking logic for answers"""
    
    def __init__(self, scoring_values: List[int]):
        self.scoring_values = scoring_values
    
    def rank_answers(self, answers: List[Dict]) -> Tuple[List[Dict], int, int]:
        """Rank all correct answers by responseCount, keep incorrect answers unranked"""
        if not answers:
            return answers, 0, 0
        
        logger.debug(f"Processing {len(answers)} answers for ranking")
        
        correct_answers, incorrect_answers = self._separate_answers(answers)
        ranked_correct, answers_ranked, answers_scored = self._rank_correct_answers(correct_answers)
        processed_incorrect = self._reset_incorrect_answers(incorrect_answers)
        
        # Combine: correct answers first (ranked), then incorrect answers
        all_answers = ranked_correct + processed_incorrect
        
        logger.debug(f"Ranking complete: {answers_ranked} ranked, {answers_scored} scored")
        return all_answers, answers_ranked, answers_scored
    
    def _separate_answers(self, answers: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Separate correct and incorrect answers"""
        correct_answers = [a for a in answers if a.get(AnswerFields.IS_CORRECT, False)]
        incorrect_answers = [a for a in answers if not a.get(AnswerFields.IS_CORRECT, False)]
        
        logger.debug(f"Found {len(correct_answers)} correct answers, {len(incorrect_answers)} incorrect answers")
        return correct_answers, incorrect_answers
    
    def _rank_correct_answers(self, correct_answers: List[Dict]) -> Tuple[List[Dict], int, int]:
        """Rank and score correct answers by responseCount"""
        if not correct_answers:
            return [], 0, 0
        
        # Sort by responseCount (highest first)
        correct_answers.sort(key=lambda x: x.get(AnswerFields.RESPONSE_COUNT, 0), reverse=True)
        
        answers_ranked = 0
        answers_scored = 0
        
        for i, answer in enumerate(correct_answers):
            rank = i + 1
            score = self.scoring_values[i] if i < len(self.scoring_values) else 0
            
            answer[AnswerFields.RANK] = rank
            answer[AnswerFields.SCORE] = score
            answers_ranked += 1
            
            if score > 0:
                answers_scored += 1
            
            self._log_answer_ranking(answer, rank, score)
        
        return correct_answers, answers_ranked, answers_scored
    
    def _reset_incorrect_answers(self, incorrect_answers: List[Dict]) -> List[Dict]:
        """Set incorrect answers to rank=0, score=0"""
        for answer in incorrect_answers:
            answer[AnswerFields.RANK] = 0
            answer[AnswerFields.SCORE] = 0
            logger.debug(f"Set incorrect answer '{answer.get(AnswerFields.ANSWER, '')[:30]}...' to rank=0, score=0")
        
        return incorrect_answers
    
    def _log_answer_ranking(self, answer: Dict, rank: int, score: int) -> None:
        """Log individual answer ranking details"""
        logger.debug(f"Ranked answer '{answer.get(AnswerFields.ANSWER, '')[:30]}...' - "
                    f"rank: {rank}, score: {score}, responseCount: {answer.get(AnswerFields.RESPONSE_COUNT, 0)}")


class QuestionProcessor:
    """Handles processing of individual questions"""
    
    def __init__(self, answer_ranker: AnswerRanker):
        self.answer_ranker = answer_ranker
    
    def process_question(self, question: Dict) -> Tuple[Dict, int, int]:
        """Process ranking for a single question"""
        question_id = QuestionFormatter.get_question_id(question)
        
        if not self._should_process_question(question, question_id):
            return question, 0, 0
        
        self._log_question_processing_start(question, question_id)
        
        ranked_answers, answers_ranked, answers_scored = self.answer_ranker.rank_answers(question['answers'])
        question['answers'] = ranked_answers
        
        self._log_question_processing_complete(question_id, answers_ranked, answers_scored)
        
        return question, answers_ranked, answers_scored
    
    def _should_process_question(self, question: Dict, question_id: str) -> bool:
        """Check if question should be processed"""
        if not question.get('answers'):
            logger.debug(f"Skipping question {question_id} - no answers")
            return False
        
        has_correct_answers = any(a.get(AnswerFields.IS_CORRECT, False) for a in question['answers'])
        if not has_correct_answers:
            logger.debug(f"Skipping question {question_id} - {ErrorMessages.NO_CORRECT_ANSWERS}")
            return False
        
        return True
    
    def _log_question_processing_start(self, question: Dict, question_id: str) -> None:
        """Log details before processing question"""
        logger.debug(f"Processing ranking for question {question_id} with {len(question['answers'])} answers")
        
        for i, answer in enumerate(question['answers']):
            logger.debug(f"Answer {i}: '{answer.get(AnswerFields.ANSWER, '')[:50]}...' - "
                        f"isCorrect: {answer.get(AnswerFields.IS_CORRECT)}, "
                        f"responseCount: {answer.get(AnswerFields.RESPONSE_COUNT, 0)}")
    
    def _log_question_processing_complete(self, question_id: str, answers_ranked: int, answers_scored: int) -> None:
        """Log completion details"""
        logger.debug(f"Question {question_id}: ranked {answers_ranked} answers, scored {answers_scored} answers")


class RankingService:
    """Main service for handling answer ranking operations"""
    
    def __init__(self, db_handler):
        self.db = db_handler
        self.answer_ranker = AnswerRanker(Config.SCORING_VALUES)
        self.question_processor = QuestionProcessor(self.answer_ranker)
        logger.info(f"RankingService initialized with scoring values: {Config.SCORING_VALUES}")
    
    def rank_and_score_answers(self, answers: List[Dict]) -> Tuple[List[Dict], int, int]:
        """Rank all correct answers by responseCount, keep incorrect answers unranked"""
        return self.answer_ranker.rank_answers(answers)
    
    def process_question_ranking(self, question: Dict) -> Tuple[Dict, int, int]:
        """Process ranking for a single question"""
        return self.question_processor.process_question(question)
    
    def validate_question_data(self, question: Dict) -> bool:
        """Validate question data before sending to API"""
        return DataValidator.validate_question(question)
    
    def process_all_questions(self) -> Dict:
        """Process ranking for all questions and update database"""
        try:
            logger.info(LogMessages.PROCESSING_START)
            
            # Fetch all questions
            questions = self._fetch_questions()
            if not questions:
                logger.warning("No questions found in API")
                return self._create_empty_result()
            
            logger.info(f"Found {len(questions)} questions to process for ranking")
            
            # Process questions for ranking
            processing_result = self._process_questions_batch(questions)
            
            # Update processed questions in database
            update_result = self._update_processed_questions(processing_result['processed_questions'])
            
            # Combine and return results
            combined_result = self._combine_results(processing_result, update_result, len(questions))
            
            logger.info(LogMessages.PROCESSING_COMPLETE)
            logger.info(f"Results: {combined_result['updated_count']} updated, "
                       f"{combined_result['failed_count']} failed, "
                       f"{combined_result['answers_ranked']} answers ranked")
            
            return combined_result
            
        except Exception as e:
            logger.error(LogMessages.PROCESSING_FAILED.format(error=str(e)))
            raise
    
    def _validate_question_for_final_submission(self, question: Dict) -> bool:
        """Validate if question meets final submission requirements - ONLY Input type questions"""
        question_id = QuestionFormatter.get_question_id(question)
        question_type = question.get('questionType', '').lower()
        
        # BASED ON DEBUG EVIDENCE: Only Input type questions are accepted
        if question_type != 'input':
            logger.debug(f"Question {question_id} is {question_type} type - only Input questions go to final")
            return False
        
        if not question.get('answers'):
            logger.debug(f"Question {question_id} has no answers")
            return False
        
        all_answers = question.get('answers', [])
        return self._validate_input_question_for_final(question_id, all_answers)

    def _validate_input_question_for_final(self, question_id: str, all_answers: List[Dict]) -> bool:
        """Validate Input question for final submission"""
        # Count correct answers with rank > 0 and score > 0
        valid_correct_answers = sum(1 for answer in all_answers 
                                  if (answer.get('isCorrect') is True and 
                                      answer.get('rank', 0) > 0 and 
                                      answer.get('score', 0) > 0))
        
        # Server requirement: exactly 3 correct answers (we take top 3)
        if valid_correct_answers < 3:
            logger.info(f"📋 Input question {question_id} needs more correct answers for final submission: "
                    f"has {valid_correct_answers}, needs 3 minimum")
            return False
        else:
            logger.info(f"✅ Input question {question_id} ready for final submission: "
                    f"{valid_correct_answers} correct answers (will use top 3)")
            return True

    def get_final_submission_summary(self, questions: List[Dict]) -> Dict:
        """Get summary of questions ready for final submission - Input type only"""
        summary = {
            "total_questions": len(questions),
            "total_input_questions": 0,
            "total_mcq_questions": 0,
            "ready_for_final": 0,
            "needs_more_answers": 0,
            "non_eligible_questions": 0,
            "by_type": {}
        }
        
        for question in questions:
            question_type = question.get('questionType', 'Unknown')
            
            if question_type not in summary["by_type"]:
                summary["by_type"][question_type] = {
                    "total": 0,
                    "ready": 0,
                    "needs_more": 0,
                    "note": ""
                }
            
            summary["by_type"][question_type]["total"] += 1
            
            if question_type.lower() == 'input':
                summary["total_input_questions"] += 1
                if self._validate_question_for_final_submission(question):
                    summary["ready_for_final"] += 1
                    summary["by_type"][question_type]["ready"] += 1
                else:
                    # Check if it's because of minimum answer requirement
                    correct_count = sum(1 for a in question.get('answers', []) 
                                    if a.get('isCorrect') and a.get('rank', 0) > 0)
                    
                    if 0 < correct_count < 3:
                        summary["needs_more_answers"] += 1
                        summary["by_type"][question_type]["needs_more"] += 1
            
            elif question_type.lower() == 'mcq':
                summary["total_mcq_questions"] += 1
                summary["non_eligible_questions"] += 1
                summary["by_type"][question_type]["note"] = "Ranked only (final endpoint rejects MCQ with 400 error)"
            
            else:
                summary["non_eligible_questions"] += 1
                summary["by_type"][question_type]["note"] = "Not submitted to final (Input only based on debug evidence)"
        
        return summary

    def process_all_questions_with_final_submission(self) -> Dict:
        """Process ranking for all questions and submit final results with update logic for existing questions"""
        try:
            logger.info(LogMessages.PROCESSING_START)
            
            # Step 1: Process ranking (existing functionality for ALL question types)
            ranking_result = self.process_all_questions()
            
            # Step 2: Get final submission summary before submitting
            if ranking_result["updated_count"] > 0:
                logger.info("🏆 Ranking completed successfully, analyzing final submission readiness...")
                
                # Fetch the updated questions with rankings
                updated_questions = self._fetch_questions()
                
                # Get final submission summary
                final_summary = self.get_final_submission_summary(updated_questions)
                
                logger.info("📊 Final Submission Analysis:")
                logger.info(f"   Total Questions: {final_summary['total_questions']}")
                logger.info(f"   Ready for Final: {final_summary['ready_for_final']}")
                logger.info(f"   Need More Answers: {final_summary['needs_more_answers']}")
                logger.info(f"   Input Questions: {final_summary['total_input_questions']}")
                logger.info(f"   MCQ Questions: {final_summary['total_mcq_questions']}")
                logger.info(f"   Non-Eligible Questions: {final_summary['non_eligible_questions']}")
                
                # Log by question type with updated requirements
                for q_type, stats in final_summary['by_type'].items():
                    if q_type.lower() == 'input':
                        logger.info(f"   {q_type}: {stats['ready']}/{stats['total']} ready for final")
                        if stats['needs_more'] > 0:
                            logger.warning(f"     ⚠️ {stats['needs_more']} {q_type} questions need more correct answers (min 3)")
                    elif q_type.lower() == 'mcq':
                        logger.info(f"   {q_type}: {stats['total']} total (ranked but not submitted to final - server rejects MCQ)")
                    else:
                        logger.info(f"   {q_type}: {stats['total']} total (not submitted to final)")
                
                # Submit to final endpoint with update logic (Input questions only)
                if final_summary['ready_for_final'] > 0:
                    logger.info(f"📤 Proceeding with final submission of {final_summary['ready_for_final']} Input questions...")
                    logger.info("💡 Note: Will update existing questions if answers have changed")
                    final_result = self.db.submit_final_questions(updated_questions)
                else:
                    logger.warning("⚠️ No Input questions ready for final submission - skipping final submission")
                    final_result = {
                        "submitted_count": 0,
                        "total_processed": len(updated_questions),
                        "success": False,
                        "message": "No Input questions met requirements for final submission"
                    }
                
                # Combine results with update details
                combined_result = ranking_result.copy()
                combined_result.update({
                    "final_submitted_count": final_result["submitted_count"],
                    "final_submission_success": final_result.get("success", False),
                    "final_submission_message": final_result.get("message", ""),
                    "final_ready_count": final_summary['ready_for_final'],
                    "final_needs_more_count": final_summary['needs_more_answers'],
                    "final_submission_details": final_result.get("details", {})
                })
                
                # Enhanced success/failure logging
                if final_result.get("success"):
                    details = final_result.get("details", {})
                    new_count = details.get("new_submitted", 0)
                    updated_count = details.get("updated", 0)
                    unchanged_count = details.get("unchanged", 0)
                    
                    message_parts = []
                    if new_count > 0:
                        message_parts.append(f"{new_count} new questions submitted")
                    if updated_count > 0:
                        message_parts.append(f"{updated_count} questions updated")
                    if unchanged_count > 0:
                        message_parts.append(f"{unchanged_count} questions unchanged")
                    
                    final_message = "; ".join(message_parts) if message_parts else "processed"
                    
                    logger.info(f"🎉 Complete process finished! Ranked {ranking_result['updated_count']} questions, "
                            f"final submission: {final_message}")
                            
                elif final_summary['ready_for_final'] == 0:
                    logger.info(f"ℹ️ Ranking completed but no Input questions ready for final submission")
                else:
                    # Check if it was a "no changes" scenario vs actual failure
                    if "No changes detected" in final_result.get("message", ""):
                        logger.info(f"ℹ️ Ranking completed, final collection already up to date")
                    else:
                        logger.warning(f"⚠️ Ranking completed but final submission failed: {final_result.get('message', 'Unknown error')}")
                
                return combined_result
            else:
                logger.info("ℹ️ No questions were updated with rankings, skipping final submission")
                ranking_result.update({
                    "final_submitted_count": 0,
                    "final_submission_success": False,
                    "final_submission_message": "No ranked questions to submit",
                    "final_ready_count": 0,
                    "final_needs_more_count": 0,
                    "final_submission_details": {}
                })
                return ranking_result
                
        except Exception as e:
            logger.error(f"❌ Complete process failed: {str(e)}")
            logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
            raise
    
    def _fetch_questions(self) -> List[Dict]:
        """Fetch all questions from database"""
        questions = self.db.fetch_all_questions()
        
        if not questions:
            logger.warning("No questions found in API")
        
        return questions
    
    def _create_empty_result(self) -> Dict:
        """Create empty result when no questions found"""
        return {
            "total_questions": 0,
            "processed_count": 0,
            "skipped_count": 0,
            "updated_count": 0,
            "failed_count": 0,
            "answers_ranked": 0,
            "answers_scored": 0
        }
    
    def _process_questions_batch(self, questions: List[Dict]) -> Dict:
        """Process a batch of questions for ranking"""
        processed_questions = []
        total_answers_ranked = 0
        total_answers_scored = 0
        processed_count = 0
        skipped_count = 0
        validation_failed = 0
        
        for question in questions:
            result = self._process_single_question_in_batch(question)
            
            if result['processed']:
                processed_questions.append(result['question'])
                total_answers_ranked += result['answers_ranked']
                total_answers_scored += result['answers_scored']
                processed_count += 1
            elif result['validation_failed']:
                validation_failed += 1
            else:
                skipped_count += 1
        
        logger.info(f"Processing complete: {processed_count} processed, {skipped_count} skipped, {validation_failed} validation failed")
        logger.info(f"Total answers ranked: {total_answers_ranked}, scored: {total_answers_scored}")
        
        return {
            'processed_questions': processed_questions,
            'processed_count': processed_count,
            'skipped_count': skipped_count,
            'validation_failed': validation_failed,
            'total_answers_ranked': total_answers_ranked,
            'total_answers_scored': total_answers_scored
        }
    
    def _process_single_question_in_batch(self, question: Dict) -> Dict:
        """Process a single question within a batch"""
        question_id = QuestionFormatter.get_question_id(question)
        
        # Check if question has answers and correct answers
        if not question.get('answers'):
            logger.debug(f"⏭️ Skipped question {question_id} - no answers")
            return {'processed': False, 'validation_failed': False}
        
        has_correct = any(a.get(AnswerFields.IS_CORRECT, False) for a in question['answers'])
        if not has_correct:
            logger.debug(f"⏭️ Skipped question {question_id} - {ErrorMessages.NO_CORRECT_ANSWERS}")
            return {'processed': False, 'validation_failed': False}
        
        # Process the question
        logger.debug(f"Processing question {question_id}...")
        processed_question, answers_ranked, answers_scored = self.question_processor.process_question(question)
        
        # Validate the processed question
        if not DataValidator.validate_question(processed_question):
            logger.error(ErrorMessages.VALIDATION_FAILED.format(id=question_id))
            return {'processed': False, 'validation_failed': True}
        
        logger.debug(f"✅ Processed question {question_id}")
        return {
            'processed': True,
            'validation_failed': False,
            'question': processed_question,
            'answers_ranked': answers_ranked,
            'answers_scored': answers_scored
        }
    
    def _update_processed_questions(self, processed_questions: List[Dict]) -> Dict:
        """Update processed questions in the database"""
        if not processed_questions:
            logger.warning("No questions to update")
            return {"updated_count": 0, "failed_count": 0}
        
        logger.info(f"Updating {len(processed_questions)} questions in API")
        
        # Log sample question structure
        self._log_sample_question_structure(processed_questions[0])
        
        return self.db.bulk_update_questions(processed_questions)
    
    def _log_sample_question_structure(self, sample_question: Dict) -> None:
        """Log sample question structure for debugging"""
        import json
        logger.debug("Sample question structure being sent:")
        sample_structure = {
            "questionID": sample_question.get('_id') or sample_question.get('questionID'),
            "answers": [{
                "answer": a.get(AnswerFields.ANSWER),
                "isCorrect": a.get(AnswerFields.IS_CORRECT),
                "responseCount": a.get(AnswerFields.RESPONSE_COUNT),
                "rank": a.get(AnswerFields.RANK),
                "score": a.get(AnswerFields.SCORE),
                "answerID": a.get('_id') or a.get('answerID', 'NO_ID')
            } for a in sample_question.get('answers', [])[:1]]  # Just first answer for brevity
        }
        logger.debug(json.dumps(sample_structure, indent=2))
    
    def _combine_results(self, processing_result: Dict, update_result: Dict, total_questions: int) -> Dict:
        """Combine processing and update results"""
        return {
            "total_questions": total_questions,
            "processed_count": processing_result['processed_count'],
            "skipped_count": processing_result['skipped_count'],
            "updated_count": update_result["updated_count"],
            "failed_count": update_result["failed_count"],
            "answers_ranked": processing_result['total_answers_ranked'],
            "answers_scored": processing_result['total_answers_scored'],
            "validation_failed": processing_result['validation_failed']
        }