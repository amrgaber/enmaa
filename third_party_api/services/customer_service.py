"""Customer service for third-party API."""
import logging
from typing import Any

from odoo import models

from ..core.constants import (
    SUCCESS_CUSTOMER_CREATED,
    SUCCESS_CUSTOMER_UPDATED,
    ERROR_INTERNAL,
)

_logger = logging.getLogger(__name__)


class ThirdPartyCustomerService(models.AbstractModel):
    """Service for customer create/update operations from API."""

    _name = 'third.party.customer.service'
    _description = 'Third Party Customer Service'

    def create_or_update_customer(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create or update a customer based on reference.

        Args:
            data: Validated request data containing:
                - reference: Unique identifier
                - name: Customer name
                - tax_id: Optional VAT number
                - city: Optional city
                - country: Optional country name/code
                - street: Optional street address

        Returns:
            dict with success status and customer details or error
        """
        try:
            Partner = self.env['res.partner']
            reference = data.get('reference')
            
            # Search for existing customer by ref field
            customer = Partner.search([('ref', '=', reference)], limit=1)
            
            # Prepare values
            vals = self._prepare_customer_vals(data)
            
            if customer:
                # Update existing customer
                customer.write(vals)
                _logger.info(
                    "Updated customer '%s' (ID: %d) via ref: %s",
                    customer.name, customer.id, reference
                )
                return {
                    'success': True,
                    'message': SUCCESS_CUSTOMER_UPDATED,
                    'customer_id': customer.id,
                    'customer_name': customer.name,
                    'reference': reference,
                    'action': 'updated',
                }
            else:
                # Create new customer
                vals['ref'] = reference
                vals['company_type'] = 'company'  # Customer is a company
                customer = Partner.create(vals)
                _logger.info(
                    "Created customer '%s' (ID: %d) via ref: %s",
                    customer.name, customer.id, reference
                )
                return {
                    'success': True,
                    'message': SUCCESS_CUSTOMER_CREATED,
                    'customer_id': customer.id,
                    'customer_name': customer.name,
                    'reference': reference,
                    'action': 'created',
                }

        except Exception as e:
            _logger.error("Error in create_or_update_customer: %s", str(e))
            return {
                'success': False,
                'error': ERROR_INTERNAL.format(str(e)),
            }

    def _prepare_customer_vals(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Prepare customer field values from API data.

        Args:
            data: Request data

        Returns:
            dict of field values for res.partner
        """
        vals = {
            'name': data.get('name'),
        }

        # Optional fields
        if data.get('tax_id'):
            vals['vat'] = data['tax_id']

        if data.get('street'):
            vals['street'] = data['street']

        if data.get('city'):
            vals['city'] = data['city']

        if data.get('country'):
            # Try to find country by name or code
            country = self._resolve_country(data['country'])
            if country:
                vals['country_id'] = country.id

        return vals

    def _resolve_country(self, country_input: str):
        """
        Find country by name or code.

        Args:
            country_input: Country name or ISO code

        Returns:
            res.country record or False
        """
        Country = self.env['res.country']
        
        # Try by code first (case-insensitive)
        country = Country.search([('code', '=ilike', country_input)], limit=1)
        if country:
            return country
        
        # Try by name (case-insensitive)
        country = Country.search([('name', '=ilike', country_input)], limit=1)
        return country
