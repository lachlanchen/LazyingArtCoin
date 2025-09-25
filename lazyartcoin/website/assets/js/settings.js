(() => {
    const artifactUrl = "assets/abi/LazyArtCoin.json";
    let artifact;
    let walletProvider;
    let signer;
    let walletAddress;
    let currentNetwork;

    const elements = {
        connectBtn: document.getElementById("connect-wallet"),
        walletStatus: document.getElementById("wallet-status"),
        networkStatus: document.getElementById("network-status"),
        contractStatus: document.getElementById("contract-status"),
        deployForm: document.getElementById("deploy-form"),
        ownerInput: document.getElementById("owner-input"),
        treasuryInput: document.getElementById("treasury-input"),
        supplyInput: document.getElementById("supply-input"),
        networkSelect: document.getElementById("network-select"),
        deployOutput: document.getElementById("deploy-output"),
        contractInput: document.getElementById("contract-input"),
        saveContractBtn: document.getElementById("save-contract"),
        refreshStatsBtn: document.getElementById("refresh-stats"),
        contractMetrics: document.getElementById("contract-metrics"),
        mintTreasuryForm: document.getElementById("mint-treasury-form"),
        mintTreasuryAmount: document.getElementById("mint-treasury-amount"),
        mintAddressForm: document.getElementById("mint-address-form"),
        mintRecipient: document.getElementById("mint-recipient"),
        mintAmount: document.getElementById("mint-amount"),
        setTreasuryForm: document.getElementById("set-treasury-form"),
        newTreasury: document.getElementById("new-treasury"),
        pauseBtn: document.getElementById("pause-token"),
        unpauseBtn: document.getElementById("unpause-token"),
        renounceBtn: document.getElementById("renounce-ownership")
    };

    const STORAGE_KEYS = {
        contract: "lac:contractAddress",
        owner: "lac:ownerAddress",
        treasury: "lac:treasuryAddress",
        supply: "lac:initialSupply"
    };

    const formatAmount = (value) => {
        if (!value) {
            return "0";
        }
        const num = Number(ethers.formatUnits(value, 18));
        if (num >= 1_000_000) {
            return `${num.toLocaleString(undefined, { maximumFractionDigits: 2 })} LAC`;
        }
        if (num >= 1) {
            return `${num.toLocaleString(undefined, { maximumFractionDigits: 4 })} LAC`;
        }
        return `${num.toFixed(6)} LAC`;
    };

    const updateWalletStatus = (text) => {
        if (elements.walletStatus) {
            elements.walletStatus.textContent = text;
        }
    };

    const updateNetworkStatus = (chainId) => {
        let name = "Unknown";
        if (chainId === 1) name = "Ethereum Mainnet";
        if (chainId === 11155111) name = "Sepolia Testnet";
        currentNetwork = chainId;
        elements.networkStatus.textContent = `${name} (Chain ID: ${chainId})`;
    };

    const ensureWallet = async (desiredChainId) => {
        if (!window.ethereum) {
            throw new Error("MetaMask not detected. Install the extension and refresh.");
        }
        walletProvider = new ethers.BrowserProvider(window.ethereum);
        const accounts = await walletProvider.send("eth_requestAccounts", []);
        signer = await walletProvider.getSigner();
        walletAddress = await signer.getAddress();
        updateWalletStatus(`Connected: ${walletAddress}`);

        const { chainId } = await walletProvider.getNetwork();
        updateNetworkStatus(Number(chainId));

        if (desiredChainId && Number(chainId) !== desiredChainId) {
            await switchNetwork(desiredChainId);
        }

        return { signer, chainId: desiredChainId || Number(chainId) };
    };

    const switchNetwork = async (chainId) => {
        if (!window.ethereum) {
            throw new Error("MetaMask not detected");
        }
        const hexChain = `0x${chainId.toString(16)}`;
        try {
            await window.ethereum.request({
                method: "wallet_switchEthereumChain",
                params: [{ chainId: hexChain }]
            });
            updateNetworkStatus(chainId);
        } catch (switchError) {
            if (switchError.code === 4902) {
                const params = chainId === 11155111
                    ? {
                        chainId: hexChain,
                        chainName: "Sepolia Test Network",
                        nativeCurrency: { name: "Sepolia ETH", symbol: "ETH", decimals: 18 },
                        rpcUrls: ["https://sepolia.infura.io/v3/"]
                    }
                    : {
                        chainId: hexChain,
                        chainName: "Ethereum Mainnet",
                        nativeCurrency: { name: "Ether", symbol: "ETH", decimals: 18 },
                        rpcUrls: ["https://mainnet.infura.io/v3/"]
                    };
                await window.ethereum.request({ method: "wallet_addEthereumChain", params: [params] });
            } else {
                throw switchError;
            }
        }
    };

    const loadArtifact = async () => {
        const res = await fetch(artifactUrl);
        if (!res.ok) {
            throw new Error("Unable to load contract artifact.");
        }
        artifact = await res.json();
    };

    const getStoredContract = () => localStorage.getItem(STORAGE_KEYS.contract) || "";

    const setContractStatus = (address) => {
        if (address && ethers.isAddress(address)) {
            elements.contractStatus.textContent = address;
        } else {
            elements.contractStatus.textContent = "Not selected";
        }
    };

    const loadFormDefaults = () => {
        const storedOwner = localStorage.getItem(STORAGE_KEYS.owner);
        const storedTreasury = localStorage.getItem(STORAGE_KEYS.treasury);
        const storedSupply = localStorage.getItem(STORAGE_KEYS.supply);
        const storedContract = getStoredContract();

        if (storedOwner && elements.ownerInput) {
            elements.ownerInput.value = storedOwner;
        }
        if (storedTreasury && elements.treasuryInput) {
            elements.treasuryInput.value = storedTreasury;
        }
        if (storedSupply && elements.supplyInput) {
            elements.supplyInput.value = storedSupply;
        }
        if (storedContract && elements.contractInput) {
            elements.contractInput.value = storedContract;
        }
        setContractStatus(storedContract);
    };

    const handleDeploy = async (evt) => {
        evt.preventDefault();
        if (!artifact) {
            await loadArtifact();
        }

        const desiredChain = Number(elements.networkSelect.value || 1);
        try {
            await ensureWallet(desiredChain);
        } catch (err) {
            updateWalletStatus(err.message);
            return;
        }

        const ownerValue = elements.ownerInput.value.trim() || walletAddress;
        const treasuryValue = elements.treasuryInput.value.trim() || ownerValue;
        const supplyValue = elements.supplyInput.value.trim();

        if (!ethers.isAddress(ownerValue)) {
            elements.deployOutput.textContent = "Owner address is invalid.";
            return;
        }
        if (!ethers.isAddress(treasuryValue)) {
            elements.deployOutput.textContent = "Treasury address is invalid.";
            return;
        }

        let initialSupply = 0n;
        if (supplyValue) {
            try {
                initialSupply = BigInt(supplyValue);
            } catch (err) {
                elements.deployOutput.textContent = "Initial supply must be a whole number.";
                return;
            }
        }

        elements.deployOutput.textContent = "Deploying LazyArtCoin… confirm the transaction in MetaMask.";

        try {
            const factory = new ethers.ContractFactory(artifact.abi, artifact.bytecode, signer);
            const contract = await factory.deploy(ownerValue, treasuryValue, initialSupply);
            await contract.waitForDeployment();
            const address = await contract.getAddress();

            const receipt = await contract.deploymentTransaction().wait();

            localStorage.setItem(STORAGE_KEYS.contract, address);
            localStorage.setItem(STORAGE_KEYS.owner, ownerValue);
            localStorage.setItem(STORAGE_KEYS.treasury, treasuryValue);
            localStorage.setItem(STORAGE_KEYS.supply, supplyValue || "0");

            if (elements.contractInput) {
                elements.contractInput.value = address;
            }
            setContractStatus(address);

            const explorerBase = desiredChain === 1 ? "https://etherscan.io/address/" : "https://sepolia.etherscan.io/address/";
            elements.deployOutput.textContent = [
                "LazyArtCoin deployed successfully!",
                `Contract address: ${address}`,
                `Explorer link: ${explorerBase}${address}`,
                `Transaction hash: ${receipt.hash}`
            ].join("\n");
        } catch (err) {
            console.error(err);
            elements.deployOutput.textContent = `Deployment failed: ${err.message}`;
        }
    };

    const getActiveContract = (requireSigner = true) => {
        const address = elements.contractInput.value.trim() || getStoredContract();
        if (!address || !ethers.isAddress(address)) {
            throw new Error("Set a valid contract address first.");
        }
        if (requireSigner && !signer) {
            throw new Error("Connect MetaMask before performing this action.");
        }
        const provider = requireSigner ? signer : walletProvider || ethers.getDefaultProvider("mainnet");
        return new ethers.Contract(address, artifact.abi, provider);
    };

    const saveContract = () => {
        const address = elements.contractInput.value.trim();
        if (!ethers.isAddress(address)) {
            alert("Enter a valid contract address.");
            return;
        }
        localStorage.setItem(STORAGE_KEYS.contract, address);
        setContractStatus(address);
        alert("Contract address saved.");
    };

    const refreshStats = async () => {
        try {
            if (!artifact) {
                await loadArtifact();
            }
            const contract = getActiveContract(false);
            const provider = walletProvider || ethers.getDefaultProvider(currentNetwork || 1);
            const [name, symbol, totalSupply, treasuryAddress] = await Promise.all([
                contract.name(),
                contract.symbol(),
                contract.totalSupply(),
                contract.treasury()
            ]);
            const treasuryBalance = await contract.balanceOf(treasuryAddress);
            let walletBalance = null;
            if (walletAddress) {
                walletBalance = await contract.balanceOf(walletAddress);
            }

            elements.contractMetrics.innerHTML = `
                <div class="metric">
                    <span class="label">Token</span>
                    <span class="value">${name} (${symbol})</span>
                </div>
                <div class="metric">
                    <span class="label">Total Supply</span>
                    <span class="value">${formatAmount(totalSupply)}</span>
                </div>
                <div class="metric">
                    <span class="label">Treasury</span>
                    <span class="value">${treasuryAddress}</span>
                </div>
                <div class="metric">
                    <span class="label">Treasury Balance</span>
                    <span class="value">${formatAmount(treasuryBalance)}</span>
                </div>
                ${walletBalance !== null ? `
                <div class="metric">
                    <span class="label">Your Balance</span>
                    <span class="value">${formatAmount(walletBalance)}</span>
                </div>` : ``}
            `;
        } catch (err) {
            console.error(err);
            alert(err.message);
        }
    };

    const handleMintTreasury = async (evt) => {
        evt.preventDefault();
        try {
            await ensureWallet();
            if (!artifact) {
                await loadArtifact();
            }
            const contract = getActiveContract();
            const amount = elements.mintTreasuryAmount.value.trim();
            if (!amount) {
                throw new Error("Provide an amount to mint.");
            }
            let parsed;
            try {
                parsed = BigInt(amount);
            } catch (err) {
                throw new Error("Amount must be a whole number.");
            }
            const tx = await contract.mintToTreasury(parsed);
            await tx.wait();
            alert(`Minted ${amount} LAC to treasury.`);
            refreshStats();
        } catch (err) {
            console.error(err);
            alert(err.message);
        }
    };

    const handleMintAddress = async (evt) => {
        evt.preventDefault();
        try {
            await ensureWallet();
            if (!artifact) {
                await loadArtifact();
            }
            const contract = getActiveContract();
            const recipient = elements.mintRecipient.value.trim();
            const amount = elements.mintAmount.value.trim();
            if (!ethers.isAddress(recipient)) {
                throw new Error("Recipient address is invalid.");
            }
            if (!amount) {
                throw new Error("Enter an amount to mint.");
            }
            let parsed;
            try {
                parsed = BigInt(amount);
            } catch (err) {
                throw new Error("Amount must be a whole number.");
            }
            const tx = await contract.mintTo(recipient, parsed);
            await tx.wait();
            alert(`Minted ${amount} LAC to ${recipient}.`);
            refreshStats();
        } catch (err) {
            console.error(err);
            alert(err.message);
        }
    };

    const handleSetTreasury = async (evt) => {
        evt.preventDefault();
        try {
            await ensureWallet();
            if (!artifact) {
                await loadArtifact();
            }
            const contract = getActiveContract();
            const newAddress = elements.newTreasury.value.trim();
            if (!ethers.isAddress(newAddress)) {
                throw new Error("Treasury address is invalid.");
            }
            const tx = await contract.setTreasury(newAddress);
            await tx.wait();
            alert(`Treasury updated to ${newAddress}.`);
            refreshStats();
        } catch (err) {
            console.error(err);
            alert(err.message);
        }
    };

    const handlePause = async () => {
        try {
            await ensureWallet();
            if (!artifact) {
                await loadArtifact();
            }
            const contract = getActiveContract();
            const tx = await contract.pause();
            await tx.wait();
            alert("Token transfers paused.");
        } catch (err) {
            console.error(err);
            alert(err.message);
        }
    };

    const handleUnpause = async () => {
        try {
            await ensureWallet();
            if (!artifact) {
                await loadArtifact();
            }
            const contract = getActiveContract();
            const tx = await contract.unpause();
            await tx.wait();
            alert("Token transfers resumed.");
        } catch (err) {
            console.error(err);
            alert(err.message);
        }
    };

    const handleRenounce = async () => {
        if (!confirm("Renouncing ownership is irreversible. Continue?")) {
            return;
        }
        try {
            await ensureWallet();
            if (!artifact) {
                await loadArtifact();
            }
            const contract = getActiveContract();
            const tx = await contract.renounceOwnership();
            await tx.wait();
            alert("Ownership renounced. Admin functions are no longer callable.");
        } catch (err) {
            console.error(err);
            alert(err.message);
        }
    };

    const init = async () => {
        loadFormDefaults();
        try {
            await loadArtifact();
        } catch (err) {
            console.error(err);
            elements.deployOutput.textContent = err.message;
        }
    };

    if (elements.connectBtn) {
        elements.connectBtn.addEventListener("click", async () => {
            try {
                await ensureWallet();
                refreshStats();
            } catch (err) {
                console.error(err);
                updateWalletStatus(err.message);
            }
        });
    }

    if (elements.deployForm) {
        elements.deployForm.addEventListener("submit", handleDeploy);
    }

    if (elements.saveContractBtn) {
        elements.saveContractBtn.addEventListener("click", saveContract);
    }

    if (elements.refreshStatsBtn) {
        elements.refreshStatsBtn.addEventListener("click", refreshStats);
    }

    if (elements.mintTreasuryForm) {
        elements.mintTreasuryForm.addEventListener("submit", handleMintTreasury);
    }

    if (elements.mintAddressForm) {
        elements.mintAddressForm.addEventListener("submit", handleMintAddress);
    }

    if (elements.setTreasuryForm) {
        elements.setTreasuryForm.addEventListener("submit", handleSetTreasury);
    }

    if (elements.pauseBtn) {
        elements.pauseBtn.addEventListener("click", handlePause);
    }

    if (elements.unpauseBtn) {
        elements.unpauseBtn.addEventListener("click", handleUnpause);
    }

    if (elements.renounceBtn) {
        elements.renounceBtn.addEventListener("click", handleRenounce);
    }

    window.addEventListener("load", init);
})();
