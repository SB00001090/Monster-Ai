package ai.monster.callguard.billing

import android.app.Activity
import android.content.Context
import com.android.billingclient.api.AcknowledgePurchaseParams
import com.android.billingclient.api.BillingClient
import com.android.billingclient.api.BillingClientStateListener
import com.android.billingclient.api.BillingFlowParams
import com.android.billingclient.api.BillingResult
import com.android.billingclient.api.ProductDetails
import com.android.billingclient.api.Purchase
import com.android.billingclient.api.PurchasesUpdatedListener
import com.android.billingclient.api.QueryProductDetailsParams
import com.android.billingclient.api.QueryPurchasesParams
import ai.monster.callguard.BuildConfig

/**
 * Google Play one-time purchase — no subscription.
 * Product: monster_callguard_lifetime (configure in Play Console with regional pricing).
 */
class BillingManager(
    private val context: Context,
    private val trialManager: TrialManager,
    private val onStateChanged: () -> Unit,
) : PurchasesUpdatedListener {

    private var productDetails: ProductDetails? = null
    var lastError: String? = null
        private set

    private val billingClient: BillingClient = BillingClient.newBuilder(context)
        .setListener(this)
        .enablePendingPurchases()
        .build()

    fun start() {
        billingClient.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(result: BillingResult) {
                if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                    queryProduct()
                    restorePurchases()
                } else {
                    lastError = result.debugMessage
                }
            }

            override fun onBillingServiceDisconnected() {
                // BillingClient auto-reconnects on next call
            }
        })
    }

    private fun queryProduct() {
        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(
                listOf(
                    QueryProductDetailsParams.Product.newBuilder()
                        .setProductId(BuildConfig.BILLING_PRODUCT_LIFETIME)
                        .setProductType(BillingClient.ProductType.INAPP)
                        .build(),
                ),
            )
            .build()
        billingClient.queryProductDetailsAsync(params) { result, list ->
            if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                productDetails = list.firstOrNull()
                onStateChanged()
            }
        }
    }

    fun formattedPrice(): String =
        productDetails?.oneTimePurchaseOfferDetails?.formattedPrice ?: "—"

    fun launchPurchase(activity: Activity) {
        val details = productDetails ?: run {
            lastError = "Product not loaded"
            return
        }
        val productParams = BillingFlowParams.ProductDetailsParams.newBuilder()
            .setProductDetails(details)
            .build()
        val flowParams = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(listOf(productParams))
            .build()
        billingClient.launchBillingFlow(activity, flowParams)
    }

    fun restorePurchases() {
        billingClient.queryPurchasesAsync(
            QueryPurchasesParams.newBuilder()
                .setProductType(BillingClient.ProductType.INAPP)
                .build(),
        ) { result, purchases ->
            if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                purchases.forEach { handlePurchase(it) }
            }
        }
    }

    override fun onPurchasesUpdated(result: BillingResult, purchases: MutableList<Purchase>?) {
        if (result.responseCode == BillingClient.BillingResponseCode.OK && purchases != null) {
            purchases.forEach { handlePurchase(it) }
        } else if (result.responseCode != BillingClient.BillingResponseCode.USER_CANCELED) {
            lastError = result.debugMessage
        }
        onStateChanged()
    }

    private fun handlePurchase(purchase: Purchase) {
        if (purchase.products.contains(BuildConfig.BILLING_PRODUCT_LIFETIME) &&
            purchase.purchaseState == Purchase.PurchaseState.PURCHASED
        ) {
            if (!purchase.isAcknowledged) {
                val ack = AcknowledgePurchaseParams.newBuilder()
                    .setPurchaseToken(purchase.purchaseToken)
                    .build()
                billingClient.acknowledgePurchase(ack) { }
            }
            trialManager.setPurchased(true)
            onStateChanged()
        }
    }

    fun destroy() {
        billingClient.endConnection()
    }
}