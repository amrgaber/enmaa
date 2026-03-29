# Third Party API - Complete Endpoint Guide

## 📋 Table of Contents
1. [Authentication](#authentication)
2. [Customer Endpoint](#1-customer-endpoint)
3. [Debtor Endpoint](#2-debtor-endpoint)
4. [Contact Endpoint](#3-contact-endpoint)
5. [Invoice Endpoint](#4-invoice-endpoint)
6. [Payment Endpoint](#5-payment-endpoint)

---

## 🔐 Authentication

All endpoints require **JWT Bearer Token** authentication.

### How to Get a Token:
1. Use the authentication endpoint from `fastapi_v19_authentication` module
2. Include in headers: `Authorization: Bearer YOUR_TOKEN`

### Rate Limiting:
All endpoints are rate-limited to prevent abuse.

---

## 1. Customer Endpoint

### Purpose
Create or update customer (company) records in Odoo.

### URL
`POST /api/v1/partners/customer`

### Logic
- **Searches** for existing customer by `reference`
- **If found**: Updates the customer with new data
- **If not found**: Creates a new customer

### Request Body

```json
{
  "reference": "CUST-001",
  "name": "ABC Company LLC",
  "taxid": "123456789",
  "city": "Cairo",
  "country": "Egypt",
  "street": "123 Business Street"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reference` | string | ✅ Yes | Unique identifier for the customer |
| `name` | string | ✅ Yes | Customer company name |
| `taxid` | string | ❌ No | Tax ID / VAT number |
| `city` | string | ❌ No | City name |
| `country` | string | ❌ No | Country name or ISO code (e.g., "Egypt" or "EG") |
| `street` | string | ❌ No | Street address |

### Response

```json
{
  "success": true,
  "message": "Customer updated successfully",
  "customer_id": 125,
  "customer_name": "ABC Company LLC",
  "reference": "CUST-001",
  "action": "updated",
  "error": null
}
```

### Use Cases
- ✅ Sync customer master data from external ERP
- ✅ Update customer information from CRM
- ✅ Create new customers from web forms

---

## 2. Debtor Endpoint

### Purpose
Create a **billing contact** (debtor) linked to an existing customer company.

### URL
`POST /api/v1/partners/debtor`

### Logic
- **Searches** for parent customer by `reference`
- **Creates** a new contact with `type='invoice'` (billing address)
- **Links** the contact to the parent customer

### Request Body

```json
{
  "reference": "CUST-001",
  "name": "John Doe - Billing Contact"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `reference` | string | ✅ Yes | Reference of the **parent customer** (company) |
| `name` | string | ✅ Yes | Name of the billing contact person |

### Response

```json
{
  "success": true,
  "message": "Debtor created successfully",
  "debtor_id": 456,
  "debtor_name": "John Doe - Billing Contact",
  "parent_customer_id": 125,
  "parent_customer_name": "ABC Company LLC",
  "error": null
}
```

### Use Cases
- ✅ Create billing contacts for invoicing
- ✅ Set up invoice recipients separate from main company
- ✅ Manage accounts payable contacts

---

## 3. Contact Endpoint

### Purpose
Create a **general contact** linked to an existing customer or debtor.

### URL
`POST /api/v1/partners/contact`

### Logic
- **Searches** for parent using priority: `debtor_id` → `customer_id`
- **Creates** a new contact with `type='contact'`
- **Links** the contact to the parent

### Request Body

```json
{
  "debtor_id": 456,
  "customer_id": null,
  "name": "Jane Smith - Sales Manager",
  "phone": "+20 123 456 7890",
  "email": "jane.smith@abccompany.com",
  "mobile": "+20 100 123 4567"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `debtor_id` | integer | ⚠️ Either/Or | Debtor ID (checked first) |
| `customer_id` | integer | ⚠️ Either/Or | Customer ID (checked second) |
| `name` | string | ✅ Yes | Contact person name |
| `phone` | string | ❌ No | Phone number |
| `email` | string | ❌ No | Email address |
| `mobile` | string | ❌ No | Mobile number |

**Note:** You must provide at least one of `debtor_id` or `customer_id`.

### Response

```json
{
  "success": true,
  "message": "Contact created successfully",
  "contact_id": 789,
  "contact_name": "Jane Smith - Sales Manager",
  "parent_id": 456,
  "parent_name": "John Doe - Billing Contact",
  "error": null
}
```

### Use Cases
- ✅ Create multiple contact persons per customer
- ✅ Store contact details for communication
- ✅ Organize customer hierarchy

---

## 4. Invoice Endpoint

### Purpose
Create **customer invoices** (sales invoices) with multiple line items.

### URL
`POST /api/v1/partners/invoice`

### Logic
1. **Resolves partner** using priority: `debtor_id` → `customer_id` → `contact_id`
2. **Finds analytic plan** (facility type) by `reference` field
3. **Finds journal** by `reference` field
4. **Creates or finds** analytic account (payout) by name
5. **Resolves currency** by code
6. **Finds products** by name (with fallback to template name)
7. **Creates invoice** with all lines
8. **Removes all taxes** automatically
9. **Sets analytic distribution** to the payout account

### Request Body

```json
{
  "debtor_id": null,
  "customer_id": 125,
  "contact_id": null,
  "facility_type_code": "1",
  "journal_code": "1",
  "invoice_date": "2026-02-07",
  "due_date": "2026-03-07",
  "contract_number": "CON-2026-0045",
  "payout_name": "Project_Alpha_Payout",
  "currency": "EGP",
  "lines": [
    {
      "product_name": "Consultancy",
      "price": 5000,
      "quantity": 2
    },
    {
      "product_name": "Software License",
      "price": 8500,
      "quantity": 1
    }
  ]
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `debtor_id` | integer | ⚠️ Either/Or | Partner ID (priority 1) |
| `customer_id` | integer | ⚠️ Either/Or | Partner ID (priority 2) |
| `contact_id` | integer | ⚠️ Either/Or | Partner ID (priority 3) |
| `facility_type_code` | string | ✅ Yes | Analytic Plan **reference** (from Configuration) |
| `journal_code` | string | ✅ Yes | Journal **reference** (from Configuration) |
| `invoice_date` | string | ✅ Yes | Invoice date (YYYY-MM-DD) |
| `due_date` | string | ✅ Yes | Payment due date (YYYY-MM-DD) |
| `contract_number` | string | ❌ No | Contract reference number |
| `payout_name` | string | ✅ Yes | Analytic account name (auto-creates if not exists) |
| `currency` | string | ❌ No | Currency code (e.g., "EGP", "USD") |
| `lines` | array | ✅ Yes | At least one invoice line required |
| `lines[].product_name` | string | ✅ Yes | Exact product name from Odoo |
| `lines[].price` | number | ✅ Yes | Unit price |
| `lines[].quantity` | number | ❌ No | Quantity (default: 1) |

**Note:** You must provide at least one of the partner IDs.

### Response

```json
{
  "success": true,
  "message": "Customer invoice created successfully",
  "invoice_id": 234,
  "invoice_name": null,
  "partner_id": 125,
  "partner_name": "ABC Company LLC",
  "payout_id": 567,
  "payout_name": "Project_Alpha_Payout",
  "error": null
}
```

**Note:** `invoice_name` is `null` for draft invoices. It gets assigned when posted.

### Before Using This Endpoint

1. ✅ **Set Reference on Analytic Plan:**
   - Go to: Configuration > Analytic Accounting > Analytic Plans
   - Open your plan (e.g., "Project")
   - Set **Reference** = "1" (or any code you want)
   - Save

2. ✅ **Set Reference on Journal:**
   - Go to: Configuration > Accounting > Journals
   - Open your journal (e.g., "Sales")
   - Set **Reference** = "1" (or any code you want)
   - Save

3. ✅ **Ensure Products Exist:**
   - Go to: Products
   - Make sure products exist with exact names you'll use in API

### Use Cases
- ✅ Generate invoices from external systems
- ✅ Automate billing workflows
- ✅ Create invoices from time tracking systems

---

## 5. Payment Endpoint

### Purpose
Create **incoming payments** (customer payments) with check/cheque details.

### URL
`POST /api/v1/partners/payment`

### Logic
1. **Resolves check name partner** using priority: `debtor_id` → `customer_id` → `contact_id`
2. **Finds payment partner** by `customer_name` search
3. **Finds journal** by `reference` field
4. **Finds check status** by `code` field
5. **Finds cheque type** by `code` field
6. **Finds payout** (analytic account) by `code` field
7. **Resolves currency** by code
8. **Creates payment** with automatic:
   - Payment type: "inbound" (receive money)
   - Receipt date: Today
   - Due date: 1 month from today
9. **Auto-confirms payment** if journal reference contains "cover", "check", or "cheque"
10. **Keeps as draft** if journal reference contains "draft"

### Request Body

```json
{
  "debtor_id": 125,
  "customer_id": null,
  "contact_id": null,
  "customer_name": "ABC Company LLC",
  "memo": "Payment for Invoice INV/2026/00001",
  "cheque_number": "CHQ-123456",
  "amount": 10000,
  "check_status_code": "PENDING",
  "payout_code": "PAY-9988",
  "cheque_type_code": "BANK",
  "journal_code": "1",
  "currency": "EGP"
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `debtor_id` | integer | ⚠️ Either/Or | Partner ID for check name (priority 1) |
| `customer_id` | integer | ⚠️ Either/Or | Partner ID for check name (priority 2) |
| `contact_id` | integer | ⚠️ Either/Or | Partner ID for check name (priority 3) |
| `customer_name` | string | ❌ No | Customer name to search as payment partner |
| `memo` | string | ❌ No | Payment memo/reference |
| `cheque_number` | string | ✅ Yes | Cheque/check number |
| `amount` | number | ✅ Yes | Payment amount (must be > 0) |
| `check_status_code` | string | ✅ Yes | Check status **code** (from Configuration) |
| `payout_code` | string | ✅ Yes | Payout analytic account **code** |
| `cheque_type_code` | string | ✅ Yes | Cheque type **code** (from Configuration) |
| `journal_code` | string | ✅ Yes | Journal **reference** |
| `currency` | string | ❌ No | Currency code (e.g., "EGP", "USD") |

### Response

```json
{
  "success": true,
  "message": "Payment created successfully",
  "payment_id": 890,
  "payment_name": "PAY/2026/00045",
  "partner_id": 125,
  "partner_name": "ABC Company LLC",
  "check_name": "ABC Company LLC",
  "state": "posted",
  "error": null
}
```

### Before Using This Endpoint

1. ✅ **Configure Check Status:**
   - Go to: Configuration > Third Party API > Check Statuses
   - Create statuses with codes (e.g., "PENDING", "CLEARED", "BOUNCED")

2. ✅ **Configure Cheque Types:**
   - Go to: Configuration > Third Party API > Cheque Types
   - Create types with codes (e.g., "BANK", "PERSONAL", "CASHIER")

3. ✅ **Set Code on Analytic Accounts:**
   - Go to: Accounting > Configuration > Analytic Accounting > Analytic Accounts
   - Open your payout account
   - Set **Code** field (e.g., "PAY-9988")

4. ✅ **Set Reference on Journal:**
   - Same as invoice endpoint

### Use Cases
- ✅ Record check/cheque payments from customers
- ✅ Track payment status and due dates
- ✅ Automate payment reconciliation

---

## 🔧 Common Setup Requirements

### 1. Upgrade the Module
After any code changes, upgrade the module:

```powershell
cd D:\odoo19
python odoo-bin -u third_party_api -d your_database_name --stop-after-init
```

### 2. Restart Odoo Server
After Python code changes (services, models):
- Stop server: `Ctrl + C`
- Start server again

### 3. Clear Browser Cache
After view changes:
- Press `Ctrl + Shift + R`

---

## 📝 Error Handling

All endpoints return errors in this format:

```json
{
  "success": false,
  "message": null,
  "error": "Detailed error message here",
  ...other fields null...
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "No valid partner found" | Invalid partner ID | Check partner exists in Odoo |
| "Facility type not found" | Invalid reference | Set Reference on Analytic Plan |
| "Journal not found" | Invalid reference | Set Reference on Journal |
| "Product not found" | Invalid product name | Use exact product name, restart server |
| "Currency not found" | Invalid currency code | Use "EGP", "USD", etc. |
| "Unauthorized" | Invalid/expired token | Get new JWT token |

---

## 🎯 Quick Testing Checklist

Before calling each endpoint:

### Customer Endpoint ✓
- [x] Have a unique reference
- [x] Have customer name

### Debtor Endpoint ✓
- [x] Parent customer exists
- [x] Have parent's reference

### Contact Endpoint ✓
- [x] Parent (customer or debtor) exists
- [x] Have parent's ID

### Invoice Endpoint ✓
- [x] Module upgraded
- [x] Server restarted
- [x] Partner exists
- [x] Analytic Plan reference set
- [x] Journal reference set
- [x] Products exist with exact names
- [x] Currency exists

### Payment Endpoint ✓
- [x] Module upgraded
- [x] Check Status configured with codes
- [x] Cheque Type configured with codes
- [x] Analytic Account has code
- [x] Journal reference set
- [x] Partner exists

---

## 🚀 Full Workflow Example

### Scenario: Create customer, invoice, and payment

```bash
# Step 1: Create Customer
POST /api/v1/partners/customer
{
  "reference": "CUST-001",
  "name": "ABC Company"
}

# Step 2: Create Debtor (Billing Contact)
POST /api/v1/partners/debtor
{
  "reference": "CUST-001",
  "name": "John Billing"
}

# Step 3: Create Invoice
POST /api/v1/partners/invoice
{
  "customer_id": 125,
  "facility_type_code": "1",
  "journal_code": "1",
  "invoice_date": "2026-02-07",
  "due_date": "2026-03-07",
  "contract_number": "CON-2026-001",
  "payout_name": "Project_Payment",
  "currency": "EGP",
  "lines": [
    {
      "product_name": "Consultancy",
      "price": 5000,
      "quantity": 10
    }
  ]
}

# Step 4: Record Payment
POST /api/v1/partners/payment
{
  "customer_id": 125,
  "customer_name": "ABC Company",
  "cheque_number": "CHQ-999",
  "amount": 50000,
  "check_status_code": "PENDING",
  "payout_code": "PAY-001",
  "cheque_type_code": "BANK",
  "journal_code": "1",
  "currency": "EGP"
}
```

---

## 📞 Support

If you encounter issues:
1. Check Odoo server logs
2. Verify all configuration is complete
3. Ensure module is upgraded and server restarted
4. Test with Swagger UI: `http://localhost:8069/api/docs`

---

**Version:** 1.0  
**Last Updated:** 2026-02-07
