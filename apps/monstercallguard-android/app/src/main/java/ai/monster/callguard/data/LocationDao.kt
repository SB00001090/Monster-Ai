package ai.monster.callguard.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query

@Dao
interface LocationDao {
    @Insert
    suspend fun insert(record: LocationRecord)

    @Query("SELECT * FROM location_records ORDER BY timestampMs DESC LIMIT :limit")
    suspend fun recent(limit: Int): List<LocationRecord>

    @Query("SELECT * FROM location_records WHERE synced = 0 ORDER BY timestampMs ASC LIMIT 50")
    suspend fun pendingSync(): List<LocationRecord>

    @Query("UPDATE location_records SET synced = 1 WHERE id IN (:ids)")
    suspend fun markSynced(ids: List<Long>)
}