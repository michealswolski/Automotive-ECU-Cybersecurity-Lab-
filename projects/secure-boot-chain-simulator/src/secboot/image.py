"""The `.sbi` boot image container: pack, parse, and the structural checks.

Models the fixed-layout image header a mask-ROM parses at power-on. Two
properties matter and both are visible in the code below:

* **Fixed size, no dynamic allocation.** The header is exactly 128 bytes at a
  known offset, so a ROM with a few hundred bytes of stack can read it.
* **Every length is validated before it is used.** Attacker-controlled length
  fields are the classic bootloader vulnerability; `parse()` proves the declared
  lengths fit the buffer before slicing anything out of it.

All multi-byte integers are big-endian, the automotive convention.

`parse()` never raises. A malformed buffer is data, not a programmer error, so
it comes back as a `ReasonCode`.
"""

from __future__ import annotations

import hashlib
import struct
import zlib
from dataclasses import dataclass

from .algo import spec_for
from .reasons import ReasonCode

#: ASCII "SBI1" — Secure Boot Image, container version 1.
MAGIC = b"SBI1"
HEADER_VERSION = 1
HEADER_LEN = 128
#: The header bytes covered by the signature: everything except the trailing
#: CRC32. The CRC is a corruption detector, never a security control, so it is
#: deliberately left outside the signed region.
SIGNED_HEADER_LEN = 0x7C
RESERVED_LEN = 28

#: `struct` format for header[0x00:0x7C]. `>` is big-endian throughout.
_SIGNED_FMT = ">4sHHIIIIHH32sI32s28s"
_CRC_FMT = ">I"

STAGE_SBL = 1
STAGE_APP = 2
STAGE_NAMES = {STAGE_SBL: "SBL", STAGE_APP: "APP"}


@dataclass(frozen=True)
class ImageHeader:
    """The 128-byte container header, unpacked."""

    stage_id: int
    svn: int
    image_version: int
    payload_len: int
    load_address: int
    algo_id: int
    key_id: int
    payload_sha256: bytes
    sig_len: int
    signer_pubkey_sha256: bytes
    header_version: int = HEADER_VERSION
    magic: bytes = MAGIC
    reserved: bytes = b"\x00" * RESERVED_LEN

    def signed_bytes(self) -> bytes:
        """header[0x00:0x7C] — the part of the header the signature covers."""
        return struct.pack(
            _SIGNED_FMT,
            self.magic,
            self.header_version,
            self.stage_id,
            self.svn,
            self.image_version,
            self.payload_len,
            self.load_address,
            self.algo_id,
            self.key_id,
            self.payload_sha256,
            self.sig_len,
            self.signer_pubkey_sha256,
            self.reserved,
        )

    def pack(self) -> bytes:
        """The full 128-byte header, CRC32 appended."""
        signed = self.signed_bytes()
        return signed + struct.pack(_CRC_FMT, zlib.crc32(signed) & 0xFFFFFFFF)

    @property
    def stage_name(self) -> str:
        return STAGE_NAMES.get(self.stage_id, f"STAGE_{self.stage_id}")


@dataclass(frozen=True)
class ParsedImage:
    """A structurally valid image, split into its four regions."""

    header: ImageHeader
    payload: bytes
    signer_pubkey: bytes
    signature: bytes

    def signed_data(self) -> bytes:
        """Exactly what the signature is computed over: signed header || payload."""
        return self.header.signed_bytes() + self.payload

    def measurement(self) -> bytes:
        """SHA-256 over the authenticated bytes — what measured boot records.

        Note this is the *signed* region, not the whole file. Measuring the
        container framing as well would make the measurement change when the
        same content is re-signed, which breaks golden attestation for no
        security gain: the signer's key ID and public-key hash are already
        inside the signed header, so a different signer still moves the PCR.
        ADR-0003.
        """
        return hashlib.sha256(self.signed_data()).digest()


@dataclass(frozen=True)
class ParseResult:
    """Errors are values on this path, so a caller never has to catch."""

    reason: ReasonCode
    image: ParsedImage | None = None
    detail: dict[str, object] | None = None

    @property
    def ok(self) -> bool:
        return self.image is not None


def build(
    *,
    stage_id: int,
    svn: int,
    payload: bytes,
    algo_id: int,
    key_id: int,
    signer_pubkey: bytes,
    signature: bytes,
    image_version: int = 0,
    load_address: int = 0,
    reserved: bytes = b"\x00" * RESERVED_LEN,
) -> bytes:
    """Assemble a complete `.sbi` file.

    The signature has to be produced over `signing_preimage()` first, because it
    covers the header that then carries `sig_len`. `sign_and_build()` in
    `builder.py` sequences that correctly; this function is the raw assembler
    the attacker tooling also uses.
    """
    header = ImageHeader(
        stage_id=stage_id,
        svn=svn,
        image_version=image_version,
        payload_len=len(payload),
        load_address=load_address,
        algo_id=algo_id,
        key_id=key_id,
        payload_sha256=hashlib.sha256(payload).digest(),
        sig_len=len(signature),
        signer_pubkey_sha256=hashlib.sha256(signer_pubkey).digest(),
        reserved=reserved,
    )
    return header.pack() + payload + signer_pubkey + signature


def signing_preimage(
    *,
    stage_id: int,
    svn: int,
    payload: bytes,
    algo_id: int,
    key_id: int,
    signer_pubkey: bytes,
    sig_len: int,
    image_version: int = 0,
    load_address: int = 0,
    reserved: bytes = b"\x00" * RESERVED_LEN,
) -> bytes:
    """The bytes to sign, given the signature length the algorithm will produce.

    `sig_len` sits inside the signed header, so it has to be known before
    signing. For fixed-length schemes that is a constant; for DER-encoded ECDSA
    it varies by a byte or two, which `builder.py` handles by signing, checking
    the length, and re-signing if it moved.
    """
    header = ImageHeader(
        stage_id=stage_id,
        svn=svn,
        image_version=image_version,
        payload_len=len(payload),
        load_address=load_address,
        algo_id=algo_id,
        key_id=key_id,
        payload_sha256=hashlib.sha256(payload).digest(),
        sig_len=sig_len,
        signer_pubkey_sha256=hashlib.sha256(signer_pubkey).digest(),
        reserved=reserved,
    )
    return header.signed_bytes() + payload


def unpack_header(buf: bytes) -> ImageHeader:
    """Header fields, with no validation. Callers should prefer `parse()`."""
    fields = struct.unpack(_SIGNED_FMT, buf[:SIGNED_HEADER_LEN])
    return ImageHeader(
        magic=fields[0],
        header_version=fields[1],
        stage_id=fields[2],
        svn=fields[3],
        image_version=fields[4],
        payload_len=fields[5],
        load_address=fields[6],
        algo_id=fields[7],
        key_id=fields[8],
        payload_sha256=fields[9],
        sig_len=fields[10],
        signer_pubkey_sha256=fields[11],
        reserved=fields[12],
    )


def parse(buf: bytes, expected_stage_id: int) -> ParseResult:
    """Structural verification — steps 1 to 7 of SPEC section 4.

    Runs strictly in that order and returns on the first failure, so the caller
    can prove from the returned code alone that no later check ran. Nothing
    cryptographic happens here: by the time this returns ok, the buffer is known
    to be well-formed, which is what makes the expensive checks in `verify.py`
    safe to attempt.
    """
    # 1. A buffer too short to hold a header cannot be indexed at all.
    if len(buf) < HEADER_LEN:
        return ParseResult(
            ReasonCode.IMAGE_TOO_SHORT, detail={"length": len(buf), "need": HEADER_LEN}
        )

    header = unpack_header(buf)

    # 2. Magic. Cheapest possible "is this even a boot image".
    if header.magic != MAGIC:
        return ParseResult(ReasonCode.BAD_MAGIC, detail={"magic": header.magic.hex()})

    # 3. A ROM must refuse a container version it does not understand rather
    #    than guess at the layout.
    if header.header_version != HEADER_VERSION:
        return ParseResult(
            ReasonCode.UNSUPPORTED_HEADER_VERSION,
            detail={"header_version": header.header_version},
        )

    # 4. Reserved bytes are a forward-compatibility trap: refusing non-zero now
    #    is what makes it safe to assign meaning to them in a later version.
    if header.reserved != b"\x00" * RESERVED_LEN:
        return ParseResult(ReasonCode.RESERVED_NOT_ZERO, detail={"reserved": header.reserved.hex()})

    # 5. Header CRC. A detection aid for flash bit-rot, never a security
    #    control — an attacker who edits the header simply recomputes it.
    actual_crc = struct.unpack(_CRC_FMT, buf[SIGNED_HEADER_LEN:HEADER_LEN])[0]
    expected_crc = zlib.crc32(buf[:SIGNED_HEADER_LEN]) & 0xFFFFFFFF
    if actual_crc != expected_crc:
        return ParseResult(
            ReasonCode.HEADER_CRC_MISMATCH,
            detail={"expected": f"{expected_crc:08x}", "actual": f"{actual_crc:08x}"},
        )

    # 6. Stage confusion: an SBL image presented where an app image is expected
    #    is signed by a legitimate key, so only this check catches it.
    if header.stage_id != expected_stage_id:
        return ParseResult(
            ReasonCode.WRONG_STAGE_ID,
            detail={
                "expected": STAGE_NAMES.get(expected_stage_id, expected_stage_id),
                "actual": header.stage_name,
            },
        )

    # 7. Lengths. The public key length comes from the algorithm table; if the
    #    algorithm is unknown we can still bound-check what we do know, and
    #    UNKNOWN_ALGO fires later at its own step in verify.py.
    spec = spec_for(header.algo_id)
    pubkey_len = spec.pubkey_len if spec is not None else 0
    declared = HEADER_LEN + header.payload_len + pubkey_len + header.sig_len
    exact = spec is not None
    too_long = declared > len(buf) or (exact and declared != len(buf))
    if too_long:
        return ParseResult(
            ReasonCode.LENGTH_OVERFLOW,
            detail={"declared": declared, "buffer": len(buf)},
        )

    start = HEADER_LEN
    payload = buf[start : start + header.payload_len]
    start += header.payload_len
    signer_pubkey = buf[start : start + pubkey_len]
    start += pubkey_len
    signature = buf[start : start + header.sig_len]

    return ParseResult(
        ReasonCode.ACCEPTED,
        image=ParsedImage(
            header=header,
            payload=payload,
            signer_pubkey=signer_pubkey,
            signature=signature,
        ),
    )
