package ai.monster.callguard.network

import okhttp3.RequestBody
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST

interface MonsterApiService {
    @GET("health")
    suspend fun health(): Response<ResponseBody>

    @GET("api/callguard/status")
    suspend fun callguardStatus(): Response<ResponseBody>

    @GET("api/callguard/connection")
    suspend fun connection(): Response<ResponseBody>

    @GET("api/callguard/threat-db")
    suspend fun threatDb(
        @Header("Authorization") auth: String? = null,
    ): Response<ResponseBody>

    @POST("api/callguard/analyze")
    suspend fun analyze(
        @Body body: RequestBody,
        @Header("Authorization") auth: String? = null,
    ): Response<ResponseBody>

    @POST("api/callguard/report")
    suspend fun report(
        @Body body: RequestBody,
        @Header("Authorization") auth: String? = null,
    ): Response<ResponseBody>

    @POST("api/callguard/token")
    suspend fun token(@Body body: RequestBody): Response<ResponseBody>
}