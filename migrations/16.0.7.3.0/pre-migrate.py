import logging
_logger = logging.getLogger(__name__)

def migrate(cr, version):
    _logger.info("RST Loan: Pre-migrate 16.0.7.3.0 - Fix denomination model")
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'rst_loan_payment_denomination' AND column_name = 'wizard_id'
    """)
    if cr.fetchone():
        cr.execute('ALTER TABLE rst_loan_payment_denomination DROP COLUMN wizard_id')
        _logger.info("  Dropped wizard_id from rst_loan_payment_denomination")
