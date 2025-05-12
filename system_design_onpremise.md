# System Design: Physician Q&A Mobile Chat Application (On-Premise EHR)

## 1. Overview

This document outlines the system design for a mobile chat application enabling physicians to perform question-answering (Q&A) about specific patients. The application leverages Large Language Models (LLMs) and Retrieval Augmented Generation (RAG) based on Electronic Health Records (EHR) stored **on-premise within the healthcare provider's internal server**. The application will be available on both iOS and Android platforms.

## 2. Goals

*   Provide a secure and intuitive mobile interface for physicians.
*   Enable physicians to select a patient and ask questions related to their on-premise EHR.
*   Utilize LLM and RAG to generate accurate and contextually relevant answers based solely on the selected patient's EHR.
*   Ensure HIPAA compliance and robust data security for sensitive patient information, with a focus on secure access to and processing of on-premise data.
*   Maintain a history of conversations for each patient.
*   Authenticate and authorize physicians securely.

## 3. Non-Goals

*   Real-time patient monitoring.
*   Direct modification of EHR data through the chat interface.
*   Diagnostic capabilities or treatment recommendations (the system provides information, not medical advice).
*   Support for communication between multiple physicians or with patients.
*   Cloud storage or processing of raw EHR data unless explicitly stated and secured under a BAA for specific components like LLMs (if a cloud-based LLM is used).

## 4. Key Components

### 4.1. Mobile Application (iOS & Android)
    *   **Framework**: React Native / Flutter (for cross-platform development) or Native (Swift/Kotlin).
    *   **Responsibilities**:
        *   User authentication (login/logout).
        *   Patient selection interface.
        *   Chat interface for Q&A.
        *   Displaying responses from the backend.
        *   Securely storing session tokens.
        *   Local caching of non-sensitive data for performance.

### 4.2. Backend Service
    *   **Technology**: Node.js (Express.js) / Python (Flask/Django) / Go.
    *   **Deployment**: Potentially within a DMZ or a secure segment of the provider's network, or a cloud environment with secure connectivity to on-premise resources.
    *   **Responsibilities**:
        *   API gateway for mobile app requests.
        *   User session management.
        *   Orchestrating communication between different services (Auth, On-Premise EHR Integration, LLM/RAG Service).
        *   Managing chat history.
        *   Enforcing business logic and authorization rules.

### 4.3. Authentication Service
    *   **Technology**: OAuth 2.0 / OpenID Connect provider (e.g., Keycloak, ADFS, or other enterprise identity provider used by the healthcare organization).
    *   **Responsibilities**:
        *   Verifying physician credentials against the provider's identity system.
        *   Issuing and validating access tokens.
        *   Managing user identities and roles.

### 4.4. On-Premise EHR Integration Service
    *   **Deployment**: Must be deployed within the healthcare provider's internal network, or have a secure, audited gateway component.
    *   **Responsibilities**:
        *   Securely authenticating and interfacing with the on-premise EHR system (e.g., via HL7, FHIR APIs if available, or custom integration).
        *   Fetching patient lists for authorized physicians.
        *   Retrieving specific patient EHR data based on requests from the LLM/RAG Service.
        *   Ensuring data access complies with internal security policies, RBAC, and patient consent.
        *   Transforming EHR data into a usable format for the RAG pipeline if necessary.

### 4.5. LLM & RAG Service
    *   **Deployment Options**:
        *   **Fully On-Premise**: The entire service (Vector DB, Embedding Model, LLM, RAG Orchestrator) is deployed within the provider's network. This offers maximum data control.
        *   **Hybrid**: EHR retrieval and embedding generation occur on-premise. Embeddings and questions (potentially de-identified or pseudonymized if possible, though challenging for RAG context) could be sent to a secure, BAA-covered cloud LLM. The design must prioritize keeping PHI on-premise.
    *   **Components**:
        *   **Vector Database**: Stores embeddings of EHR documents (e.g., on-premise instances of Milvus, Weaviate, or a filesystem-based solution for smaller scale).
        *   **Embedding Model**: Converts text chunks from EHR into vector embeddings (could be an open-source model run locally).
        *   **LLM**: Generates answers (e.g., open-source LLMs like Llama 2, Mistral, or others suitable for on-premise deployment, or a BAA-covered cloud LLM like Vertex AI PaLM API if PHI handling is meticulously managed).
        *   **RAG Orchestrator**:
            1.  Receives a physician's question and patient identifier.
            2.  Requests relevant EHR documents/chunks for the patient from the On-Premise EHR Integration Service.
            3.  Pre-processes and chunks EHR data.
            4.  Generates embeddings for the question and EHR chunks.
            5.  Queries the vector database to find the most relevant EHR excerpts.
            6.  Constructs a prompt for the LLM, including the question and the retrieved context.
            7.  Sends the prompt to the LLM and receives the generated answer.
            8.  (Optional) Post-processes the answer.
    *   **Responsibilities**:
        *   Processing natural language questions.
        *   Retrieving relevant information from patient EHRs via the On-Premise EHR Integration Service.
        *   Generating coherent and accurate answers based *solely* on the provided patient's EHR context.

### 4.6. Application Database
    *   **Technology**: PostgreSQL / MySQL (on-premise or in a secure cloud environment if not storing PHI).
    *   **Responsibilities**:
        *   Storing physician user profiles (non-sensitive metadata, preferences).
        *   Storing chat history (questions, answers, timestamps, patient ID association). PHI in chat history must be encrypted and access-controlled.

## 5. Architecture Diagram

```mermaid
graph TD
    subgraph Mobile Client
        MA[Mobile App iOS/Android]
    end

    subgraph Provider Network / DMZ
        API_GW[API Gateway / Backend Service]
        AUTH_SVC[Authentication Service e.g., ADFS/Keycloak]
        APP_DB[Application Database e.g., Chat History]
        
        subgraph On-Premise LLM & RAG Service (Option 1: Fully On-Premise)
            LLM_RAG_SVC_ONPREM[LLM & RAG Service (On-Prem)]
            VECTOR_DB_ONPREM[Vector Database (On-Prem)]
            LLM_MODEL_ONPREM[LLM Model (On-Prem)]
            EMBED_MODEL_ONPREM[Embedding Model (On-Prem)]
        end

        ON_PREM_EHR_INT_SVC[On-Premise EHR Integration Service]
        ON_PREM_EHR[On-Premise EHR System]
    end

    subgraph Cloud Services (Option 2: Hybrid LLM)
        LLM_RAG_SVC_HYBRID_CTRL[RAG Control Logic (On-Prem/DMZ)]
        LLM_MODEL_CLOUD[BAA-Covered Cloud LLM e.g., Vertex AI]
    end
    
    MA -- HTTPS --> API_GW
    API_GW -- Authenticates/Authorizes --> AUTH_SVC
    API_GW -- Stores/Retrieves Chat Data --> APP_DB
    
    %% Option 1: Fully On-Premise LLM/RAG
    API_GW -- Forwards Q&A Request --> LLM_RAG_SVC_ONPREM
    LLM_RAG_SVC_ONPREM -- Retrieves Patient EHR --> ON_PREM_EHR_INT_SVC
    ON_PREM_EHR_INT_SVC -- Accesses EHR --> ON_PREM_EHR
    LLM_RAG_SVC_ONPREM -- EHR Chunks for Embedding --> EMBED_MODEL_ONPREM
    LLM_RAG_SVC_ONPREM -- Stores/Queries Embeddings --> VECTOR_DB_ONPREM
    LLM_RAG_SVC_ONPREM -- Generates Answer --> LLM_MODEL_ONPREM
    LLM_RAG_SVC_ONPREM -- Returns Answer --> API_GW

    %% Option 2: Hybrid LLM (Illustrative - details depend on security)
    API_GW -- Forwards Q&A Request --> LLM_RAG_SVC_HYBRID_CTRL
    LLM_RAG_SVC_HYBRID_CTRL -- Retrieves Patient EHR --> ON_PREM_EHR_INT_SVC
    %% LLM_RAG_SVC_HYBRID_CTRL prepares context (on-prem)
    LLM_RAG_SVC_HYBRID_CTRL -- Secure Prompt (Context + Question) --> LLM_MODEL_CLOUD
    LLM_MODEL_CLOUD -- Generates Answer --> LLM_RAG_SVC_HYBRID_CTRL
    LLM_RAG_SVC_HYBRID_CTRL -- Returns Answer --> API_GW

    API_GW -- Returns Answer --> MA

    %% User Authentication Flow
    MA -- Login Request --> AUTH_SVC
    AUTH_SVC -- Issues Token --> MA
```

## 6. Data Flow (Patient Q&A - Assuming On-Premise RAG)

1.  **Physician Login**:
    *   Physician opens app, enters credentials.
    *   App sends credentials to Authentication Service (likely integrated with hospital's Active Directory/LDAP via ADFS or similar).
    *   Authentication Service verifies, returns access token. App stores token.

2.  **Patient Selection**:
    *   Physician requests patient list.
    *   App sends request (with token) to Backend Service.
    *   Backend Service verifies token, requests patient list from On-Premise EHR Integration Service.
    *   On-Premise EHR Integration Service queries the internal EHR system.
    *   List returned to app. Physician selects patient.

3.  **Question Submission**:
    *   Physician types question, submits.
    *   App sends question, patient ID, token to Backend Service.

4.  **Backend Processing & RAG (On-Premise Focus)**:
    *   Backend Service validates token, forwards question/patient ID to LLM & RAG Service (assumed on-premise).
    *   **LLM & RAG Service**:
        *   a. **EHR Retrieval**: Contacts On-Premise EHR Integration Service to fetch relevant EHR documents for the patient.
        *   b. **Chunking & Embedding**: EHR data chunked, converted to vector embeddings using an on-premise embedding model. Embeddings stored in on-premise Vector Database.
        *   c. **Query Embedding**: Question converted to vector embedding.
        *   d. **Similarity Search**: Query on-premise Vector DB for relevant EHR excerpts.
        *   e. **Prompt Construction**: Prompt created with question and retrieved context.
        *   f. **LLM Invocation**: Prompt sent to on-premise LLM.
        *   g. **Answer Generation**: LLM generates answer based *only* on provided context.

5.  **Response Delivery**:
    *   LLM & RAG Service returns answer to Backend Service.
    *   Backend Service logs Q&A in Application Database (ensure PHI encryption if stored).
    *   Backend Service sends answer to mobile app.
    *   App displays answer.

## 7. API Design (High-Level)

*(Largely similar to the cloud version, but backend endpoints are hosted differently)*
### 7.1. Authentication
*   `POST /auth/login`
*   `POST /auth/refresh`
*   `POST /auth/logout`

### 7.2. Patients
*   `GET /patients`
*   `GET /patients/{patientId}`

### 7.3. Chat
*   `POST /chat/{patientId}/query`
    *   Request Body: `{ "question": "User's question" }`
    *   Response Body: `{ "answer": "LLM generated answer", "sources": [ { "document_id": "...", "excerpt": "..." } ] }`
*   `GET /chat/{patientId}/history`

## 8. Security and Compliance

*   **HIPAA Compliance**: Critical. All components handling PHI must adhere to HIPAA.
    *   **Network Segmentation**: Isolate services handling PHI within secure network zones.
    *   **Secure Communication**: TLS/SSL for all data in transit, including internal communications between services. VPNs for remote mobile access to backend if it's hosted on-premise.
    *   **Data at Rest Encryption**: Encrypt data in Application DB, Vector DB. On-premise EHR system should already have its own encryption.
    *   **Physical Security**: For on-premise servers, ensure appropriate physical security measures.
*   **Authentication & Authorization**:
    *   Integrate with hospital's existing Identity Provider (e.g., Active Directory via ADFS, SAML, OAuth2/OIDC).
    *   Strong MFA for physicians.
    *   RBAC enforced at all levels, especially for EHR access.
*   **Data Minimization**: Only necessary PHI is retrieved and processed.
*   **Audit Trails**: Comprehensive logging of data access, queries, system actions. Logs stored securely.
*   **PHI Handling in LLM/RAG**:
    *   **On-Premise LLM**: Preferred for maximum control. Ensure the LLM and its environment are hardened.
    *   **Cloud LLM (Hybrid)**: If used, PHI (context) must be sent via a secure, BAA-covered channel. Data must not be retained or used for training by the LLM provider beyond what's agreed in the BAA. This is a high-risk area requiring careful vetting.
    *   Strictly limit context to the current patient's EHR.
*   **Mobile App Security**: Secure token storage, OWASP Mobile Top 10. No PHI caching on device unless encrypted and essential.
*   **On-Premise EHR System Security**: Rely on and complement the existing security of the EHR system. The integration service must use least privilege access.

## 9. Scalability and Performance

*   **Backend & LLM/RAG Services (On-Premise)**:
    *   Horizontal scaling using virtualization, containers (Docker, Kubernetes on-premise).
    *   Requires provider to have adequate server infrastructure (CPU, GPU for LLM/embeddings, RAM, storage).
*   **On-Premise EHR Integration Service**: Performance depends on the EHR system's API capabilities and internal network bandwidth.
*   **Vector Database (On-Premise)**: Choose a solution that can scale with the volume of EHR data and query load.
*   **LLM Inference (On-Premise)**: GPU resources are critical for good performance.
*   **Asynchronous Processing**: Consider for RAG pipeline to improve mobile app responsiveness.

## 10. Deployment

*   **Mobile App**: App Store, Google Play Store.
*   **Backend Components (API Gateway, Auth Service, App DB, LLM/RAG Service, EHR Integration Service)**:
    *   Deployed within the healthcare provider's data center.
    *   May involve DMZ for internet-facing components (like API Gateway if mobile app connects directly from internet).
    *   Secure VPN for mobile app access if backend is not exposed to internet.
    *   Requires coordination with provider's IT infrastructure team.
*   **Infrastructure Management**: Provider's existing tools for server provisioning, monitoring, and maintenance. IaC (e.g., Ansible, Chef, Puppet for on-premise) can be beneficial.

## 11. Technology Stack Summary (Proposed On-Premise Focus)

*   **Mobile**: React Native or Flutter, or Swift/Kotlin.
*   **Backend**: Node.js/Express.js or Python/Flask.
*   **Authentication**: Hospital's Identity Provider (e.g., ADFS, Keycloak).
*   **Application Database**: PostgreSQL / MySQL (on-premise).
*   **On-Premise EHR Integration**: Custom development based on EHR's API (FHIR, HL7, proprietary) or existing integration engines.
*   **LLM & RAG (On-Premise Option)**:
    *   **Vector DB**: Milvus, Weaviate (self-hosted).
    *   **Embedding Model**: Sentence Transformers (e.g., from Hugging Face, run locally).
    *   **LLM**: Open-source models like Llama 2, Mistral (self-hosted on GPU servers).
*   **Deployment**: On-premise servers, VMs, potentially on-premise Kubernetes.

## 12. Future Considerations

*   **Hybrid Cloud Scenarios**: Exploring secure use of cloud resources (e.g., for scalable LLM inference under BAA if on-premise GPU capacity is a constraint) while keeping PHI processing primarily on-premise.
*   **EHR Event-Driven Updates**: Mechanism to update vector embeddings when EHR data changes.
*   **Advanced De-identification**: If any data needs to leave the trusted boundary for specialized processing (e.g., analytics), robust de-identification is key.
*   **Federated Learning**: If multiple provider sites adopt similar systems, exploring federated learning for model improvement without sharing raw PHI.

This document provides a foundational system design for an on-premise EHR context. Each component and integration point, especially with the internal EHR system, will require detailed specification and close collaboration with the healthcare provider's IT and security teams.
