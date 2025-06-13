#!/usr/bin/env python3
"""
Refactored One-time ranking processor with Final Submission
Clean, modular, and easy to understand
"""

import sys
import time
from typing import Dict
from config.settings import Config
from database.db_handler import DatabaseHandler
from services.ranking_service import RankingService
from utils.logger import setup_logger


class ProcessorDisplay:
    """Handles console output and display formatting"""
    
    @staticmethod
    def print_header():
        """Print application header"""
        print("🚀 Starting Survey Answer Ranking & Final Submission Processor")
        print("=" * 70)
    
    @staticmethod
    def print_results(result: Dict, processing_time: float):
        """Print processing results including final submission in a formatted way"""
        print("\n" + "=" * 70)
        print("📊 COMPLETE RANKING & FINAL SUBMISSION RESULTS")
        print("=" * 70)
        print(f"⏱️  Processing Time: {processing_time}s")
        print(f"📝 Total Questions: {result['total_questions']}")
        print(f"✅ Processed: {result['processed_count']}")
        print(f"⏭️  Skipped: {result['skipped_count']}")
        print(f"💾 Updated in Database: {result['updated_count']}")
        print(f"❌ Failed Updates: {result['failed_count']}")
        print(f"🏆 Answers Ranked: {result['answers_ranked']}")
        print(f"🎯 Answers Scored: {result['answers_scored']}")
        
        # Final submission results
        if 'final_submitted_count' in result:
            print(f"🚀 Final Submitted: {result['final_submitted_count']}")
            if result.get('final_submission_success'):
                print(f"✅ Final Submission: Success")
            else:
                print(f"❌ Final Submission: Failed - {result.get('final_submission_message', 'Unknown error')}")
            
            # Show final submission readiness summary
            if 'final_ready_count' in result:
                print(f"📋 Ready for Final: {result['final_ready_count']}")
            if 'final_needs_more_count' in result and result['final_needs_more_count'] > 0:
                print(f"⚠️  Need More Answers: {result['final_needs_more_count']} (Input type needs min 5)")
        
        ProcessorDisplay._print_warnings_and_success(result)
        
        print("=" * 70)
        print("🏁 Complete process finished. Application will now exit.")
    
    @staticmethod
    def _print_warnings_and_success(result: Dict):
        """Print warnings and success messages based on results including final submission"""
        if result['failed_count'] > 0:
            print(f"\n⚠️  Warning: {result['failed_count']} questions failed to update")
        
        if result['updated_count'] > 0:
            print(f"\n🎉 Success! {result['updated_count']} questions updated with rankings")
            
            # Final submission success message
            if result.get('final_submitted_count', 0) > 0:
                print(f"🚀 Success! {result['final_submitted_count']} questions submitted to final collection")
            elif 'final_submission_success' in result and not result['final_submission_success']:
                if result.get('final_ready_count', 0) == 0:
                    print(f"\n ℹ️ No questions ready for final submission (need more correct answers)")
                else:
                    print(f"\n⚠️  Warning: Final submission failed - {result.get('final_submission_message', 'Unknown error')}")
        else:
            print(f"\n ℹ️ No questions were updated (possibly no correct answers found)")
    
    @staticmethod
    def print_error(error_msg: str):
        """Print error message"""
        print(f"\n❌ Error: {error_msg}")
        print("🔧 Check your .env file and API configuration")


class ProcessorValidator:
    """Handles validation of processor prerequisites"""
    
    @staticmethod
    def validate_configuration(logger) -> bool:
        """Validate configuration and log results"""
        try:
            Config.validate()
            logger.info("✅ Configuration validated")
            logger.info(f"📡 API URL: {Config.get_full_api_url()}")
            return True
        except Exception as e:
            logger.error(f"❌ Configuration validation failed: {str(e)}")
            return False
    
    @staticmethod
    def test_api_connection(db_handler, logger) -> bool:
        """Test API connection and log results"""
        logger.info("🔍 Testing API connection...")
        if not db_handler.test_connection():
            logger.error("❌ API connection failed. Exiting.")
            return False
        
        logger.info("✅ API connection successful!")
        return True


class RankingProcessor:
    """Main processor class that orchestrates the ranking and final submission process"""
    
    def __init__(self):
        self.logger = setup_logger()
        self.db_handler = None
        self.ranking_service = None
    
    def initialize_services(self) -> bool:
        """Initialize database handler and ranking service"""
        try:
            self.logger.info("🔧 Initializing services...")
            self.db_handler = DatabaseHandler()
            self.ranking_service = RankingService(self.db_handler)
            return True
        except Exception as e:
            self.logger.error(f"❌ Service initialization failed: {str(e)}")
            return False
    
    def validate_prerequisites(self) -> bool:
        """Validate all prerequisites before processing"""
        if not ProcessorValidator.validate_configuration(self.logger):
            return False
        
        if not self.initialize_services():
            return False
        
        if not ProcessorValidator.test_api_connection(self.db_handler, self.logger):
            return False
        
        return True
    
    def execute_ranking_process(self) -> tuple:
        """Execute the main ranking process with final submission"""
        self.logger.info("⚙️ Starting complete ranking and final submission process...")
        start_time = time.time()
        
        try:
            # Use the enhanced method that includes final submission
            result = self.ranking_service.process_all_questions_with_final_submission()
            processing_time = round(time.time() - start_time, 2)
            return result, processing_time, True
        except Exception as e:
            processing_time = round(time.time() - start_time, 2)
            self.logger.error(f"❌ Fatal error in complete ranking processor: {str(e)}")
            return None, processing_time, False
    
    def run(self) -> bool:
        """Run the complete ranking and final submission process"""
        ProcessorDisplay.print_header()
        
        # Validate prerequisites
        if not self.validate_prerequisites():
            ProcessorDisplay.print_error("Prerequisites validation failed")
            return False
        
        # Execute ranking process
        result, processing_time, success = self.execute_ranking_process()
        
        if not success:
            ProcessorDisplay.print_error("Complete ranking and final submission process execution failed")
            return False
        
        # Display results
        ProcessorDisplay.print_results(result, processing_time)
        
        # Log completion
        if result['failed_count'] > 0:
            self.logger.warning("Some updates failed. Check logs for details.")
        
        if result['updated_count'] > 0:
            if result.get('final_submission_success'):
                self.logger.info("✅ Complete ranking and final submission process completed successfully")
            elif result.get('final_ready_count', 0) == 0:
                self.logger.info("ℹ️ Ranking completed successfully but no questions ready for final submission")
            else:
                self.logger.warning("⚠️ Ranking completed but final submission failed")
        else:
            self.logger.info("ℹ️ Ranking process completed with no updates")
        
        return True


def main() -> bool:
    """Main function - entry point for the ranking processor"""
    processor = RankingProcessor()
    return processor.run()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)