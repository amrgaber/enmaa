"""Contact service for third-party API."""
import logging
from typing import Any

from odoo import models

from ..core.constants import (
    CONTACT_TYPE_CONTACT,
    SUCCESS_CONTACT_CREATED,
    ERROR_INTERNAL,
)

_logger = logging.getLogger(__name__)


class ThirdPartyContactService(models.AbstractModel):
    """Service for contact creation from API."""

    _name = 'third.party.contact.service'
    _description = 'Third Party Contact Service'

    def create_contact(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a contact with optional company linkage.

        Args:
            data: Validated request data containing:
                - reference: Unique reference for the contact
                - name: Contact name
                - company: Optional company Odoo ID to search and link
                - city: Optional city
                - country: Optional country name/code
                - street: Optional street address

        Returns:
            dict with success status and contact details or error
        """
        try:
            Partner = self.env['res.partner']
            reference = data.get('reference')
            name = data.get('name')
            company_id = data.get('company')
            
            # Prepare contact values
            contact_vals = {
                'ref': reference,
                'name': name,
                'type': CONTACT_TYPE_CONTACT,
                'company_type': 'person',
            }
            
            # Handle company linkage
            parent_company = None
            if company_id:
                # Resolve company by Odoo ID strictly
                parent_company = Partner.browse(company_id).exists()
                
                if parent_company and parent_company.is_company:
                    _logger.debug("Linked contact '%s' to company '%s' (ID: %d)", name, parent_company.name, parent_company.id)
                    contact_vals['parent_id'] = parent_company.id
                else:
                    parent_company = None  # Reset if not a valid company
                    _logger.warning("Company ID '%s' not found or is not a company for contact '%s'.", company_id, name)

            # Add optional address fields
            if data.get('street'):
                contact_vals['street'] = data['street']
            
            if data.get('city'):
                contact_vals['city'] = data['city']
            
            if data.get('country'):
                country = self._resolve_country(data['country'])
                if country:
                    contact_vals['country_id'] = country.id
            
            # Create contact
            contact = Partner.create(contact_vals)
            
            _logger.info(
                "Created contact '%s' (ID: %d, Ref: %s)%s",
                contact.name,
                contact.id,
                contact.ref or '',
                f" under company '{parent_company.name}'" if parent_company else ""
            )
            
            return {
                'success': True,
                'message': SUCCESS_CONTACT_CREATED,
                'contact_id': contact.id,
                'contact_name': contact.name,
                'reference': contact.ref,
                'parent_company_id': parent_company.id if parent_company else None,
                'parent_company_name': parent_company.name if parent_company else None,
            }

        except Exception as e:
            _logger.error("Error in create_contact: %s", str(e))
            return {
                'success': False,
                'error': ERROR_INTERNAL.format(str(e)),
            }

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
