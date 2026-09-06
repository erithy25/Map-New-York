// Reader for the pipeline's NYCB runtime container (DATA_CONTRACTS §15) and the `tiles` table (runtime/tiles.nycb).
//
// Layout: header {char magic[4]="NYCB"; uint32 version=1; uint32 section_count; uint64 index_offset}; index = array of
// {char name[16]; uint64 offset; uint64 size; uint32 element_size; uint32 element_count}; optional "strtab" section
// (uint32 offsets into a NUL-separated blob). Little-endian, float32.
//
// INTEGRATION NOTE (see unreal/COMPILE_CHECKLIST.md "core io"): the core exposes the same container through
// nycsim/io/NycbReader.h; this adapter is written against the §15 byte contract so it does not depend on the exact
// core API. When the core reader is adopted only this file changes.
#pragma once

#include "CoreMinimal.h"

struct FNYCNycbSection
{
	FString Name;
	uint64 Offset = 0;
	uint64 Size = 0;
	uint32 ElementSize = 0;
	uint32 ElementCount = 0;
};

class NYCSIMRUNTIME_API FNYCNycbFile
{
public:
	/** Loads and validates the whole file. Returns false and fills OutError on any structural problem. */
	bool Load(const FString& Path, FString& OutError);

	bool IsLoaded() const { return Data.Num() > 0; }
	uint32 Version() const { return FileVersion; }
	const TArray<FNYCNycbSection>& Sections() const { return Index; }
	const FNYCNycbSection* FindSection(const TCHAR* Name) const;

	/** Raw bytes of a section (empty view when absent). */
	TArrayView<const uint8> SectionBytes(const FNYCNycbSection& Section) const;

	/** String from the "strtab" section at a byte offset; empty when absent or out of range. */
	FString String(uint32 StrtabOffset) const;

	int64 TotalBytes() const { return Data.Num(); }
	const FString& FilePath() const { return LoadedPath; }

private:
	TArray64<uint8> Data;
	TArray<FNYCNycbSection> Index;
	const FNYCNycbSection* Strtab = nullptr;
	uint32 FileVersion = 0;
	FString LoadedPath;
};

/** One record of runtime/tiles.nycb `tiles` section (28 bytes). */
struct FNYCTileRecord
{
	int32 Tx = 0;
	int32 Ty = 0;
	float ZMin = 0.f;
	float ZMax = 0.f;
	uint32 NumBuildings = 0;
	uint32 NumProps = 0;
	uint8 Flags = 0;       // has_terrain=1, has_water=2, has_land=4
	uint8 BoroughMask = 0; // bit b set for borough code b (1 MN 2 BX 3 BK 4 QN 5 SI 6 NJ)

	bool HasTerrain() const { return (Flags & 1) != 0; }
	bool HasWater() const { return (Flags & 2) != 0; }
	bool HasLand() const { return (Flags & 4) != 0; }
	FIntPoint Tile() const { return FIntPoint(Tx, Ty); }
};

class NYCSIMRUNTIME_API FNYCTilesTable
{
public:
	static constexpr uint32 RecordSize = 28;

	/** Parses the `tiles` section of an already-loaded tiles.nycb. */
	bool Parse(const FNYCNycbFile& File, FString& OutError);

	const TArray<FNYCTileRecord>& Records() const { return Tiles; }
	const FNYCTileRecord* Find(const FIntPoint& Tile) const;
	int32 Num() const { return Tiles.Num(); }
	/** Bounding tile indices (inclusive). */
	FIntRect TileExtent() const { return Extent; }
	float GlobalZMin() const { return ZMinAll; }
	float GlobalZMax() const { return ZMaxAll; }

private:
	TArray<FNYCTileRecord> Tiles;
	TMap<FIntPoint, int32> Lookup;
	FIntRect Extent;
	float ZMinAll = 0.f;
	float ZMaxAll = 0.f;
};
