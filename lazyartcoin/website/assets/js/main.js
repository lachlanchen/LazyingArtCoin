(() => {
    const yearEl = document.getElementById("year");
    if (yearEl) {
        yearEl.textContent = new Date().getFullYear();
    }

    const CONTRACT_STORAGE_KEY = "lac:contractAddress";

    const defaultProvider = ethers.getDefaultProvider("mainnet");
    let walletProvider;
    let signer;
    let walletAddress;
    let currentContract;

    const contractAbi = [
        "function name() view returns (string)",
        "function symbol() view returns (string)",
        "function decimals() view returns (uint8)",
        "function totalSupply() view returns (uint256)",
        "function balanceOf(address account) view returns (uint256)",
        "function treasury() view returns (address)"
    ];

    const elements = {
        connect: document.getElementById("connect-wallet"),
        walletStatus: document.getElementById("wallet-status"),
        contractInput: document.getElementById("contract-input"),
        loadContract: document.getElementById("load-contract"),
        totalSupply: document.getElementById("total-supply"),
        treasuryBalance: document.getElementById("treasury-balance"),
        walletBalance: document.getElementById("wallet-balance"),
        contractAddress: document.getElementById("contract-address"),
        treasury: document.getElementById("treasury"),
        initialSupply: document.getElementById("initial-supply")
    };

    const formatLac = (rawValue) => {
        if (!rawValue) {
            return "0 LAC";
        }
        const value = Number(ethers.formatUnits(rawValue, 18));
        if (value === 0) {
            return "0 LAC";
        }
        if (value < 1) {
            return `${value.toFixed(6)} LAC`;
        }
        if (value < 1_000) {
            return `${value.toLocaleString(undefined, { maximumFractionDigits: 4 })} LAC`;
        }
        return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })} LAC`;
    };

    const updateWalletStatus = (status) => {
        if (elements.walletStatus) {
            elements.walletStatus.textContent = status;
        }
    };

    const ensureWallet = async () => {
        if (!window.ethereum) {
            throw new Error("MetaMask is required to connect a wallet.");
        }
        walletProvider = new ethers.BrowserProvider(window.ethereum);
        await walletProvider.send("eth_requestAccounts", []);
        signer = await walletProvider.getSigner();
        walletAddress = await signer.getAddress();
        updateWalletStatus(`Connected: ${walletAddress}`);
        return walletAddress;
    };

    const getReadProvider = () => {
        if (walletProvider) {
            return walletProvider;
        }
        return defaultProvider;
    };

    const loadToken = async (addressOverride) => {
        const address = (addressOverride || elements.contractInput.value || "").trim();
        if (!ethers.isAddress(address)) {
            alert("Enter a valid Ethereum address for the token contract.");
            return;
        }

        try {
            const provider = getReadProvider();
            currentContract = new ethers.Contract(address, contractAbi, provider);

            const [name, symbol, totalSupply, treasuryAddress] = await Promise.all([
                currentContract.name(),
                currentContract.symbol(),
                currentContract.totalSupply(),
                currentContract.treasury()
            ]);

            elements.contractAddress.textContent = address;
            elements.totalSupply.textContent = formatLac(totalSupply);
            elements.treasury.textContent = treasuryAddress;

            const treasuryBalance = await currentContract.balanceOf(treasuryAddress);
            elements.treasuryBalance.textContent = formatLac(treasuryBalance);

            elements.initialSupply.textContent = `${name} (${symbol}) launched with ${formatLac(totalSupply)} minted.`;

            if (walletAddress) {
                const balance = await currentContract.balanceOf(walletAddress);
                elements.walletBalance.textContent = formatLac(balance);
            } else {
                elements.walletBalance.textContent = "Connect wallet";
            }

            localStorage.setItem(CONTRACT_STORAGE_KEY, address);
        } catch (err) {
            console.error(err);
            alert("Unable to load contract data. Confirm network access and that the address is correct.");
        }
    };

    if (elements.connect) {
        elements.connect.addEventListener("click", async () => {
            try {
                await ensureWallet();
                if (currentContract) {
                    const balance = await currentContract.balanceOf(walletAddress);
                    elements.walletBalance.textContent = formatLac(balance);
                }
            } catch (err) {
                console.error(err);
                updateWalletStatus(err.message);
            }
        });
    }

    if (elements.loadContract) {
        elements.loadContract.addEventListener("click", loadToken);
    }

    window.addEventListener("load", () => {
        const stored = localStorage.getItem(CONTRACT_STORAGE_KEY);
        if (stored && ethers.isAddress(stored)) {
            elements.contractInput.value = stored;
            loadToken(stored);
        }
    });
})();
