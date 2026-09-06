#include "CoreAdapter/NYCNycb.h"
#include "NYCSimRuntime.h"

#include "HAL/FileManager.h"
#include "Misc/FileHelper.h"

namespace
{
	template <typename T>
	T ReadLE(const uint8* P)
	{
		T V;
		FMemory::Memcpy(&V, P, sizeof(T));
#if PLATFORM_LITTLE_ENDIAN
		return V;
#else
		return ByteSwap(V);
#endif
	}

	constexpr int64 HeaderSize = 20;
	constexpr int64 IndexEntrySize = 40;
}

bool FNYCNycbFile::Load(const FString& Path, FString& OutError)
{
	Data.Empty();
	Index.Empty();
	Strtab = nullptr;
	FileVersion = 0;
	LoadedPath = Path;

	if (!IFileManager::Get().FileExists(*Path))
	{
		OutError = FString::Printf(TEXT("file not found: %s"), *Path);
		return false;
	}
	if (!FFileHelper::LoadFileToArray(Data, *Path, FILEREAD_Silent))
	{
		OutError = FString::Printf(TEXT("cannot read: %s"), *Path);
		Data.Empty();
		return false;
	}
	if (Data.Num() < HeaderSize)
	{
		OutError = FString::Printf(TEXT("%s: shorter than the NYCB header (%lld bytes)"), *Path, Data.Num());
		Data.Empty();
		return false;
	}
	if (Data[0] != 'N' || Data[1] != 'Y' || Data[2] != 'C' || Data[3] != 'B')
	{
		OutError = FString::Printf(TEXT("%s: bad magic"), *Path);
		Data.Empty();
		return false;
	}
	FileVersion = ReadLE<uint32>(Data.GetData() + 4);
	const uint32 SectionCount = ReadLE<uint32>(Data.GetData() + 8);
	const uint64 IndexOffset = ReadLE<uint64>(Data.GetData() + 12);
	if (FileVersion != 1)
	{
		OutError = FString::Printf(TEXT("%s: unsupported NYCB version %u"), *Path, FileVersion);
		Data.Empty();
		return false;
	}
	if (SectionCount > 4096)
	{
		OutError = FString::Printf(TEXT("%s: implausible section count %u"), *Path, SectionCount);
		Data.Empty();
		return false;
	}
	const uint64 IndexBytes = static_cast<uint64>(SectionCount) * IndexEntrySize;
	if (IndexOffset < static_cast<uint64>(HeaderSize) || IndexOffset + IndexBytes > static_cast<uint64>(Data.Num()))
	{
		OutError = FString::Printf(TEXT("%s: index out of range (offset %llu, %u entries, file %lld bytes)"), *Path, IndexOffset, SectionCount, Data.Num());
		Data.Empty();
		return false;
	}
	Index.Reserve(SectionCount);
	for (uint32 i = 0; i < SectionCount; ++i)
	{
		const uint8* E = Data.GetData() + IndexOffset + static_cast<uint64>(i) * IndexEntrySize;
		FNYCNycbSection S;
		char NameBuf[17];
		FMemory::Memcpy(NameBuf, E, 16);
		NameBuf[16] = '\0';
		S.Name = FString(UTF8_TO_TCHAR(NameBuf));
		S.Offset = ReadLE<uint64>(E + 16);
		S.Size = ReadLE<uint64>(E + 24);
		S.ElementSize = ReadLE<uint32>(E + 32);
		S.ElementCount = ReadLE<uint32>(E + 36);
		if (S.Offset + S.Size > static_cast<uint64>(Data.Num()))
		{
			OutError = FString::Printf(TEXT("%s: section '%s' exceeds file (offset %llu size %llu)"), *Path, *S.Name, S.Offset, S.Size);
			Data.Empty();
			Index.Empty();
			return false;
		}
		if (S.ElementSize > 0 && static_cast<uint64>(S.ElementSize) * S.ElementCount > S.Size)
		{
			OutError = FString::Printf(TEXT("%s: section '%s' declares %u x %u bytes but holds %llu"), *Path, *S.Name, S.ElementCount, S.ElementSize, S.Size);
			Data.Empty();
			Index.Empty();
			return false;
		}
		Index.Add(MoveTemp(S));
	}
	Strtab = FindSection(TEXT("strtab"));
	return true;
}

const FNYCNycbSection* FNYCNycbFile::FindSection(const TCHAR* Name) const
{
	for (const FNYCNycbSection& S : Index)
	{
		if (S.Name.Equals(Name, ESearchCase::CaseSensitive))
		{
			return &S;
		}
	}
	return nullptr;
}

TArrayView<const uint8> FNYCNycbFile::SectionBytes(const FNYCNycbSection& Section) const
{
	if (Section.Offset + Section.Size > static_cast<uint64>(Data.Num()))
	{
		return TArrayView<const uint8>();
	}
	return TArrayView<const uint8>(Data.GetData() + Section.Offset, static_cast<int32>(FMath::Min<uint64>(Section.Size, MAX_int32)));
}

FString FNYCNycbFile::String(uint32 StrtabOffset) const
{
	if (!Strtab || StrtabOffset >= Strtab->Size)
	{
		return FString();
	}
	const uint8* Begin = Data.GetData() + Strtab->Offset + StrtabOffset;
	const uint8* End = Data.GetData() + Strtab->Offset + Strtab->Size;
	int32 Len = 0;
	while (Begin + Len < End && Begin[Len] != 0)
	{
		++Len;
	}
	return FString(FUTF8ToTCHAR(reinterpret_cast<const ANSICHAR*>(Begin), Len));
}

bool FNYCTilesTable::Parse(const FNYCNycbFile& File, FString& OutError)
{
	Tiles.Empty();
	Lookup.Empty();
	const FNYCNycbSection* S = File.FindSection(TEXT("tiles"));
	if (!S)
	{
		OutError = FString::Printf(TEXT("%s: no 'tiles' section"), *File.FilePath());
		return false;
	}
	if (S->ElementSize != RecordSize)
	{
		OutError = FString::Printf(TEXT("%s: 'tiles' element_size %u != %u (DATA_CONTRACTS §15 layout)"), *File.FilePath(), S->ElementSize, RecordSize);
		return false;
	}
	const TArrayView<const uint8> Bytes = File.SectionBytes(*S);
	if (static_cast<uint64>(Bytes.Num()) < static_cast<uint64>(S->ElementCount) * RecordSize)
	{
		OutError = FString::Printf(TEXT("%s: 'tiles' truncated"), *File.FilePath());
		return false;
	}
	Tiles.Reserve(S->ElementCount);
	Extent = FIntRect(0, 0, 0, 0);
	ZMinAll = TNumericLimits<float>::Max();
	ZMaxAll = TNumericLimits<float>::Lowest();
	for (uint32 i = 0; i < S->ElementCount; ++i)
	{
		const uint8* R = Bytes.GetData() + static_cast<uint64>(i) * RecordSize;
		FNYCTileRecord T;
		T.Tx = ReadLE<int32>(R + 0);
		T.Ty = ReadLE<int32>(R + 4);
		T.ZMin = ReadLE<float>(R + 8);
		T.ZMax = ReadLE<float>(R + 12);
		T.NumBuildings = ReadLE<uint32>(R + 16);
		T.NumProps = ReadLE<uint32>(R + 20);
		T.Flags = R[24];
		T.BoroughMask = R[25];
		if (!FMath::IsFinite(T.ZMin) || !FMath::IsFinite(T.ZMax) || T.ZMin > T.ZMax + 1e-3f)
		{
			OutError = FString::Printf(TEXT("%s: tile (%d,%d) has invalid z range [%f, %f]"), *File.FilePath(), T.Tx, T.Ty, T.ZMin, T.ZMax);
			Tiles.Empty();
			return false;
		}
		const FIntPoint Key(T.Tx, T.Ty);
		if (Lookup.Contains(Key))
		{
			OutError = FString::Printf(TEXT("%s: duplicate tile (%d,%d)"), *File.FilePath(), T.Tx, T.Ty);
			Tiles.Empty();
			Lookup.Empty();
			return false;
		}
		if (Tiles.Num() == 0)
		{
			Extent = FIntRect(T.Tx, T.Ty, T.Tx, T.Ty);
		}
		else
		{
			Extent.Min.X = FMath::Min(Extent.Min.X, T.Tx);
			Extent.Min.Y = FMath::Min(Extent.Min.Y, T.Ty);
			Extent.Max.X = FMath::Max(Extent.Max.X, T.Tx);
			Extent.Max.Y = FMath::Max(Extent.Max.Y, T.Ty);
		}
		ZMinAll = FMath::Min(ZMinAll, T.ZMin);
		ZMaxAll = FMath::Max(ZMaxAll, T.ZMax);
		Lookup.Add(Key, Tiles.Num());
		Tiles.Add(T);
	}
	if (Tiles.Num() == 0)
	{
		ZMinAll = ZMaxAll = 0.f;
	}
	return true;
}

const FNYCTileRecord* FNYCTilesTable::Find(const FIntPoint& Tile) const
{
	const int32* Idx = Lookup.Find(Tile);
	return Idx ? &Tiles[*Idx] : nullptr;
}
