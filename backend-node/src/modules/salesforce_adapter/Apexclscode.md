@RestResource(urlMapping='/CartApi/*')
global without sharing class CartApi {

    /* =================================================
       ADD TO CART (UNCHANGED)
       ================================================= */
    @HttpPost
    global static AddToCartResponse addToCart() {
          String traceId = 'ADD_TO_CART_' + String.valueOf(DateTime.now().getTime());
          System.debug('[' + traceId + '] START addToCart');
        RestResponse res = RestContext.response;
        AddToCartResponse out = new AddToCartResponse();

        try {
            AddToCartRequest req =
                (AddToCartRequest) JSON.deserialize(
                    RestContext.request.requestBody.toString(),
                    AddToCartRequest.class
                );
                System.debug('[' + traceId + '] Request body parsed');
                System.debug('[' + traceId + '] productId=' + req.productId + ', quantity=' + req.quantity);


            if (String.isBlank(req.productId) || req.quantity == null || req.quantity <= 0) {
                return error(out, res, 400, 'Invalid productId or quantity');
            }

            Id webStoreId = [
                SELECT Id FROM WebStore
                WHERE Name = 'EasyMart'
                LIMIT 1
            ].Id;
            System.debug('[' + traceId + '] WebStoreId=' + webStoreId);
            Id buyerAccountId = '001dL00001otSknQAE';
            
            ConnectApi.CartSummary summary =
                ConnectApi.CommerceCart.getOrCreateActiveCartSummary(
                    webStoreId,
                    buyerAccountId,
                    'active'
                );

            WebCart cart = [
                SELECT Id, AccountId
                FROM WebCart
                WHERE Id = :summary.cartId
                LIMIT 1
            ];
              
            ConnectApi.CartItemInput input = new ConnectApi.CartItemInput();
            input.productId = req.productId;
            input.quantity  = String.valueOf(req.quantity);
            input.type      = ConnectApi.CartItemType.Product;
               System.debug('[' + traceId + '] Adding item to cart');
                System.debug('[' + traceId + '] productId=' + input.productId + ', quantity=' + input.quantity);

            ConnectApi.CommerceCart.addItemToCart(
                webStoreId,
                cart.AccountId,
                cart.Id,
                input,
                UserInfo.getDefaultCurrency()
            );
            System.debug('[' + traceId + '] addItemToCart executed successfully');

            // Query the created WebCartItem to obtain the cart item Id
            CartItem createdItem = [
                SELECT Id
                FROM CartItem
                WHERE CartId = :cart.Id AND Product2Id = :req.productId
                ORDER BY CreatedDate DESC
                LIMIT 1
            ];
             System.debug('[' + traceId + '] Created CartItem=' + createdItem);

            out.success = true;
            out.cartId    = cart.Id;
            out.cartItemId = (createdItem != null) ? createdItem.Id : null;
            out.message   = 'Item added to cart';
            res.statusCode = 200;
            System.debug('[' + traceId + '] SUCCESS cartId=' + cart.Id + ', cartItemId=' + createdItem.Id);

        } catch (Exception e) {
            System.debug('[' + traceId + '] ERROR');
    System.debug('[' + traceId + '] Message=' + e.getMessage());
    System.debug('[' + traceId + '] StackTrace=' + e.getStackTraceString());
            out.success = false;
            out.message = e.getMessage();
            res.statusCode = 500;
        }

        return out;
    }

    /* =================================================
       READ CART (SOURCE OF cartItemId)
       ================================================= */
@HttpGet
global static GetCartResponse getCart() {

    RestResponse res = RestContext.response;
    RestRequest req = RestContext.request;
    GetCartResponse out = new GetCartResponse();
    out.lines = new List<CartLine>();

    try {
        Id webStoreId = [
            SELECT Id
            FROM WebStore
            WHERE Name = 'EasyMart'
            LIMIT 1
        ].Id;

        // Get buyerAccountId from query parameter, fallback to hardcoded value
        String buyerAccountIdParam = req.params.get('buyerAccountId');
        Id buyerAccountId = String.isNotBlank(buyerAccountIdParam) 
            ? (Id)buyerAccountIdParam 
            : '001dL00001otSknQAE';

        System.debug('CartApi.getCart - Using buyerAccountId: ' + buyerAccountId);

        ConnectApi.CartSummary summary =
            ConnectApi.CommerceCart.getOrCreateActiveCartSummary(
                webStoreId,
                buyerAccountId,
                'active'
            );

        WebCart cart = [
            SELECT Id
            FROM WebCart
            WHERE Id = :summary.cartId
            LIMIT 1
        ];

        // 🔴 LOOP SCOPE IS CORRECT HERE
        for (CartItem wcItem : [
            SELECT Id, Product2Id, Quantity
            FROM CartItem
            WHERE CartId = :cart.Id
        ]) {
            CartLine line = new CartLine();
            line.cartItemId = wcItem.Id;
            line.productId  = wcItem.Product2Id;
            line.quantity   = Integer.valueOf(wcItem.Quantity);
            out.lines.add(line);
        }

        out.cartId  = cart.Id;
        out.success = true;
        res.statusCode = 200;

    } catch (Exception e) {
        out.success = false;
        out.message = e.getMessage();
        res.statusCode = 500;
    }

    return out;
}

    /* =================================================
       UPDATE / DELETE CART ITEM (+ / − / 🗑️)
       ================================================= */
    @HttpPatch
    global static UpdateCartItemResponse updateCartItem() {

        RestResponse res = RestContext.response;
        UpdateCartItemResponse out = new UpdateCartItemResponse();

        try {
            UpdateCartItemRequest req =
                (UpdateCartItemRequest) JSON.deserialize(
                    RestContext.request.requestBody.toString(),
                    UpdateCartItemRequest.class
                );

            if (String.isBlank(req.cartItemId)) {
                return errorUpdate(out, res, 400, 'cartItemId is required');
            }

            Id webStoreId = [
                SELECT Id FROM WebStore
                WHERE Name = 'EasyMart'
                LIMIT 1
            ].Id;

            Id buyerAccountId = '001dL00001otSknQAE';

            ConnectApi.CartSummary summary =
                ConnectApi.CommerceCart.getOrCreateActiveCartSummary(
                    webStoreId,
                    buyerAccountId,
                    'active'
                );

            WebCart cart = [
                SELECT Id, AccountId
                FROM WebCart
                WHERE Id = :summary.cartId
                LIMIT 1
            ];

            if (req.quantity == null || req.quantity <= 0) {
                // DELETE
                ConnectApi.CommerceCart.deleteCartItem(
                    webStoreId,
                    cart.AccountId,
                    cart.Id,
                    req.cartItemId
                );
                out.cartItemId = req.cartItemId;
                out.message = 'Item removed';
            } else {
                // UPDATE
                ConnectApi.CartItemInput input = new ConnectApi.CartItemInput();
                input.quantity = String.valueOf(req.quantity);

                ConnectApi.CommerceCart.updateCartItem(
                    webStoreId,
                    cart.AccountId,
                    cart.Id,
                    req.cartItemId,
                    input
                );
                out.quantity = req.quantity;
                out.cartItemId = req.cartItemId;
                out.message  = 'Item updated';
            }

            out.success = true;
            res.statusCode = 200;

        } catch (Exception e) {
            out.success = false;
            out.message = e.getMessage();
            res.statusCode = 500;
        }

        return out;
    }

    /* =================================================
       DELETE CART ITEM (explicit DELETE handler)
       ================================================= */
    @HttpDelete
    global static DeleteCartItemResponse deleteCartItem() {

        RestResponse res = RestContext.response;
        DeleteCartItemResponse out = new DeleteCartItemResponse();

        try {
            DeleteCartItemRequest req =
                (DeleteCartItemRequest) JSON.deserialize(
                    RestContext.request.requestBody.toString(),
                    DeleteCartItemRequest.class
                );

            if (String.isBlank(req.cartItemId)) {
                return errorDelete(out, res, 400, 'cartItemId is required');
            }

            Id webStoreId = [
                SELECT Id FROM WebStore
                WHERE Name = 'EasyMart'
                LIMIT 1
            ].Id;

            Id buyerAccountId = '001dL00001otSknQAE';

            ConnectApi.CartSummary summary =
                ConnectApi.CommerceCart.getOrCreateActiveCartSummary(
                    webStoreId,
                    buyerAccountId,
                    'active'
                );

            WebCart cart = [
                SELECT Id, AccountId
                FROM WebCart
                WHERE Id = :summary.cartId
                LIMIT 1
            ];

            ConnectApi.CommerceCart.deleteCartItem(
                webStoreId,
                cart.AccountId,
                cart.Id,
                req.cartItemId
            );

            out.cartItemId = req.cartItemId;
            out.success = true;
            out.message = 'Item removed';
            res.statusCode = 200;

        } catch (Exception e) {
            out.success = false;
            out.message = e.getMessage();
            res.statusCode = 500;
        }

        return out;
    }

    /* =================================================
       DTOs
       ================================================= */
    global class AddToCartRequest {
        public String productId;
        public Integer quantity;
    }

    global class UpdateCartItemRequest {
        public String cartItemId;
        public Integer quantity;
    }

    global class AddToCartResponse {
        public Boolean success;
        public String message;
        public Id cartId;
        public String cartItemId;
    }

    global class UpdateCartItemResponse {
        public Boolean success;
        public String message;
        public Integer quantity;
        public String cartItemId;
    }

    global class DeleteCartItemRequest {
        public String cartItemId;
    }

    global class DeleteCartItemResponse {
        public Boolean success;
        public String message;
        public String cartItemId;
    }

    global class GetCartResponse {
        public Boolean success;
        public String message;
        public Id cartId;
        public List<CartLine> lines;
    }

    global class CartLine {
        public String cartItemId;
        public String productId;
        public Integer quantity;
    }

    /* =================================================
       HELPERS
       ================================================= */
    private static AddToCartResponse error(
        AddToCartResponse r,
        RestResponse res,
        Integer status,
        String msg
    ) {
        r.success = false;
        r.message = msg;
        res.statusCode = status;
        return r;
    }

    private static UpdateCartItemResponse errorUpdate(
        UpdateCartItemResponse r,
        RestResponse res,
        Integer status,
        String msg
    ) {
        r.success = false;
        r.message = msg;
        res.statusCode = status;
        return r;
    }

    private static DeleteCartItemResponse errorDelete(
        DeleteCartItemResponse r,
        RestResponse res,
        Integer status,
        String msg
    ) {
        r.success = false;
        r.message = msg;
        res.statusCode = status;
        return r;
    }
}


/**
 * CommerceSearchRest
 *
 * IMPORTANT:
 * - This Apex REST is NOT a substitute for B2B Commerce Storefront search.
 * - It provides a minimal, FLS-aware, user-mode, admin-style lookup on core objects.
 * - It does NOT attempt to replicate storefront entitlements/pricing/visibility.
 *
 * Returns internal catalog results with optional pricebook lookup and NO media URLs,
 * to avoid leaking internal org URLs or requiring user sessions in the client.
 */
@RestResource(urlMapping='/commerce/search')
global without sharing class CommerceSearchRest {

    // Request DTO
    global class SearchRequest {
        public String query;
        public Integer pageSize;
        public Id effectiveAccountId; // used only to hint pricebook; NOT identity
    }

    // Product DTO returned to caller
    global class ProductDTO {
        public Id productId;
        public String productName;
        public Decimal unitPrice;
        public String currencyIsoCode; // avoid reserved identifier 'currency'
        public String imageUrl; // intentionally left null (no internal URLs)
    }

    // Response wrapper
    global class SearchResponse {
        public List<ProductDTO> products = new List<ProductDTO>();
        public Integer totalSize = 0;
    }

    @HttpPost
    global static void doSearch() {
        RestRequest req = RestContext.request;
        RestResponse res = RestContext.response;

        try {
            if (req.requestBody == null) {
                badRequest('Missing request body');
                return;
            }

            SearchRequest sr = (SearchRequest) JSON.deserialize(req.requestBody.toString(), SearchRequest.class);

            if (sr == null || String.isBlank(sr.query)) {
                badRequest('query is required');
                return;
            }

            Integer pageSize = (sr.pageSize != null && sr.pageSize > 0) ? Integer.valueOf(Math.min(sr.pageSize, 50)) : 10;

            // Determine a pricebook hint (admin-style). This is NOT storefront pricing/entitlements.
            Id pricebookId = null;
            if (sr.effectiveAccountId != null) {
                // If your org associates accounts to pricebooks via a custom field, set the API name here.
                // Many orgs do NOT have Account.Pricebook2Id. We therefore do NOT reference it directly.
                // Option A (recommended): pass an explicit Pricebook2Id in the request instead of Account Id.
                // Option B: implement your own mapping in a custom metadata or custom field and read it here.

                // No direct Account->Pricebook2 reference. Leave pricebookId null to fall back to Standard PB.
                // If you want to support a custom mapping, add your field API name below and enable FLS checks.
                // Example:
                // if (Schema.sObjectType.Account.fields.My_Pricebook__c.isAccessible()) {
                //     Account acct = [SELECT My_Pricebook__c FROM Account WHERE Id = :sr.effectiveAccountId LIMIT 1];
                //     pricebookId = acct.My_Pricebook__c;
                // }
            }

            if (pricebookId == null) {
                // FLS/CRUD check for Pricebook2 read
                if (!Schema.sObjectType.Pricebook2.isAccessible()) {
                    forbidden('Insufficient object access for Pricebook2');
                    return;
                }
                // Query the Standard Price Book
                Pricebook2 stdPb = [
                    SELECT Id
                    FROM Pricebook2
                    WHERE IsStandard = true
                    LIMIT 1
                ];
                pricebookId = stdPb != null ? stdPb.Id : null;
            }

            // Build LIKE query
            String likeQuery = '%' + String.escapeSingleQuotes(sr.query) + '%';

            // FLS for Product2 fields
            if (!Schema.sObjectType.Product2.isAccessible()
                || !Schema.sObjectType.Product2.fields.Name.isAccessible()
                || !Schema.sObjectType.Product2.fields.IsActive.isAccessible()) {
                forbidden('Insufficient field-level access for Product2 fields');
                return;
            }

            // Query limited set of fields
            List<Product2> products = [
                SELECT Id, Name
                FROM Product2
                WHERE IsActive = true
                AND (Name LIKE :likeQuery OR (Description != null AND Description LIKE :likeQuery))
                ORDER BY Name
                LIMIT :pageSize
            ];

            List<Id> productIds = new List<Id>();
            for (Product2 p : products) productIds.add(p.Id);

            // Map PricebookEntry by Product2Id for the chosen pricebook (admin-style, not storefront derivation)
            Map<Id, PricebookEntry> pbeMap = new Map<Id, PricebookEntry>();
            if (!productIds.isEmpty() && pricebookId != null) {
                if (!Schema.sObjectType.PricebookEntry.isAccessible()
                    || !Schema.sObjectType.PricebookEntry.fields.UnitPrice.isAccessible()) {
                    // If FLS blocks price access, skip pricing silently
                } else {
                    // NOTE: CurrencyIsoCode is not available if Multi-Currency is disabled.
                    // We only select fields that exist in all orgs by default.
                    for (PricebookEntry pbe : [
                        SELECT Product2Id, UnitPrice
                        FROM PricebookEntry
                        WHERE Pricebook2Id = :pricebookId
                        AND Product2Id IN :productIds
                        AND IsActive = true
                    ]) {
                        pbeMap.put(pbe.Product2Id, pbe);
                    }
                }
            }

            // Build response (no internal Content URLs)
            SearchResponse out = new SearchResponse();
            for (Product2 p : products) {
                ProductDTO dto = new ProductDTO();
                dto.productId = p.Id;
                dto.productName = p.Name;

                PricebookEntry pbe = pbeMap.get(p.Id);
                if (pbe != null) {
                    dto.unitPrice = pbe.UnitPrice;
                } else {
                    dto.unitPrice = null;
                }
                // We cannot reliably return CurrencyIsoCode if org is not multi-currency; omit it.
                dto.currencyIsoCode = null;

                dto.imageUrl = null; // Do not emit internal shepherd links
                out.products.add(dto);
            }

            out.totalSize = out.products.size();
            ok(out);
            return;

        } catch (QueryException qe) {
            serverError('QueryException: ' + qe.getMessage());
            return;
        } catch (Exception ex) {
            serverError('Exception: ' + ex.getMessage());
            return;
        }
    }

    // Helpers

    private static void writeJson(Integer status, Object body) {
        RestResponse res = RestContext.response;
        res.addHeader('Content-Type', 'application/json');
        res.statusCode = status;
        res.responseBody = Blob.valueOf(JSON.serialize(body));
    }

    private static void writeError(Integer status, String message) {
        Map<String, Object> payload = new Map<String, Object>{
            'success' => false,
            'error' => message
        };
        writeJson(status, payload);
    }

    private static void ok(Object body) {
        writeJson(200, body);
    }

    private static void badRequest(String message) {
        writeError(400, message);
    }

    private static void forbidden(String message) {
        writeError(403, message);
    }

    private static void serverError(String message) {
        writeError(500, message);
    }
}




global without sharing class WidgetHelper {

    // Returns AccountId for the current user or null
    public static Id getAccountIdForCurrentUser() {
        Id userId = UserInfo.getUserId();
        Map<String, Schema.SObjectField> userFields = Schema.SObjectType.User.fields.getMap();

        try {
            // If User.AccountId exists in this org, prefer it
            if (userFields.containsKey('AccountId')) {
                String q = 'SELECT Id, AccountId FROM User WHERE Id = \'' + String.escapeSingleQuotes(String.valueOf(userId)) + '\' LIMIT 1';
                User u = (User) Database.query(q);
                if (u != null && u.AccountId != null) return u.AccountId;
            }

            // Otherwise, if User.ContactId exists, use Contact.AccountId
            if (userFields.containsKey('ContactId')) {
                String q2 = 'SELECT Id, ContactId FROM User WHERE Id = \'' + String.escapeSingleQuotes(String.valueOf(userId)) + '\' LIMIT 1';
                User u2 = (User) Database.query(q2);
                if (u2 != null && u2.ContactId != null) {
                    String q3 = 'SELECT AccountId FROM Contact WHERE Id = \'' + String.escapeSingleQuotes(String.valueOf(u2.ContactId)) + '\' LIMIT 1';
                    Contact c = (Contact) Database.query(q3);
                    if (c != null) return c.AccountId;
                }
            }

        } catch (Exception e) {
            System.debug('WidgetHelper.getAccountIdForCurrentUser error: ' + e.getMessage());
        }

        return null;
    }

    // LWC/Aura callable method
    @AuraEnabled(cacheable=true)
    public static String getBuyerAccountId() {
        Id acct = getAccountIdForCurrentUser();
        return acct == null ? null : String.valueOf(acct);
    }
}



@RestResource(urlMapping='/WidgetHelper/*')
global without sharing class WidgetHelperRest {
    @HttpGet
    global static String getContext() {
        Id acct = WidgetHelper.getAccountIdForCurrentUser();
        return acct == null ? '' : String.valueOf(acct);
    }
}


/**
 * ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
 * Class Name      : SessionController
 * Author          : <YourName>
 * Created Date    : Jan 16, 2026
 * Last Modified By: <YourName>
 * Last Modified On: Jan 16, 2026
 * Description     : This class implements for......
 *  
 * Change History  :
 *  Date          │   Author     │   Change
 * ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
 *  Jan 16, 2026  │ <YourName>   │ Initial version
 * ――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――――
 */

public without sharing class SessionController {
    @AuraEnabled(cacheable=false)
    public static String getSessionId() {
        return UserInfo.getSessionId();
    }
}