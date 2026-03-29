"""Debtor (invoice contact) service for third-party API."""
import logging
from typing import Any

from odoo import models

from ..core.constants import (
    CONTACT_TYPE_INVOICE,
    SUCCESS_DEBTOR_CREATED,
    ERROR_CUSTOMER_NOT_FOUND,
    ERROR_INTERNAL,
)

_logger = logging.getLogger(__name__)


class ThirdPartyDebtorService(models.AbstractModel):
    """Service for debtor (invoice contact) creation from API."""

    _name = 'third.party.debtor.service'
    _description = 'Third Party Debtor Service'

    def create_debtor(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a debtor contact linked to a customer.

        Args:
            data: Validated request data containing:
                - reference: Reference of the parent customer
                - name: Name for the debtor contact

        Returns:
            dict with success status and debtor details or error
        """
        try:
            Partner = self.env['res.partner']
            reference = data.get('reference')
            
            # Find parent customer strictly by Odoo ID
            parent_customer = False
            if reference and str(reference).isdigit():
                parent_customer = Partner.browse(int(reference)).exists()
            
            if not parent_customer:
                _logger.warning(
                    "Debtor creation failed: Customer not found for ID '%s'",
                    reference
                )
                return {
                    'success': False,
                    'error': ERROR_CUSTOMER_NOT_FOUND.format(reference),
                }
            
            # Create debtor contact
            debtor_vals = self._prepare_debtor_vals(data)
            debtor_vals.update({
                'parent_id': parent_customer.id,
                'type': CONTACT_TYPE_INVOICE,
                'company_type': 'person',
            })
            
            debtor = Partner.create(debtor_vals)
            
            _logger.info(
                "Created debtor '%s' (ID: %d) under customer '%s' (ID: %d)",
                debtor.name, debtor.id, parent_customer.name, parent_customer.id
            )
            
            return {
                'success': True,
                'message': SUCCESS_DEBTOR_CREATED,
                'debtor_id': debtor.id,
                'debtor_name': debtor.name,
                'parent_customer_id': parent_customer.id,
                'parent_customer_name': parent_customer.name,
            }

        except Exception as e:
            _logger.error("Error in create_debtor: %s", str(e))
            return {
                'success': False,
                'error': ERROR_INTERNAL.format(str(e)),
            }

    def _prepare_debtor_vals(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Prepare debtor field values from API data.

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
